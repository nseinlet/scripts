#!/usr/bin/env python3
from datetime import datetime, timedelta
import odoolib
import configparser

debug = False

config = configparser.ConfigParser()
config.read('config.ini')
user = config['CREDENTIALS']['login']
odoo_key = config['CREDENTIALS']['odoo_key']
upg_key = config['CREDENTIALS']['upg_key']
saas_ops_key = config['CREDENTIALS']['saas_ops_key']

valid_targets = config['TARGETS']['valid'].split(',')

UPGRADE_ISSUES_PROJECT_ID = 70

TASK_STAGE_CODE_REVIEW_ID = 25373
TASK_STAGE_ASSESSMENT_ID = 25372
TASK_STAGE_INTERNAL_FEEDBACK_ID = 152
TASK_STAGE_TECHNICAL_ID = 150
TASK_STAGE_FUNCTIONAL_ID = 25372
TASK_STAGE_READY_FOR_TECHNICAL_ID = 25525
TASK_STAGE_READY_FOR_FUNCTIONAL_ID = 308
TASK_STAGE_CUSTOMER_FEEDBACK_ID = 32059
TASK_STAGE_DONE_ID = 898
TASK_STAGE_CANCELLED_ID = 1241

connection = odoolib.get_connection(
    hostname="www.odoo.com",
    database="openerp",
    protocol="jsonrpcs",
    port=443,
    login=user, 
    password=odoo_key
)

upg_connection = odoolib.get_connection(
    hostname="upgrade.odoo.com",
    database="odoo_upgrade",
    protocol="jsonrpcs",
    port=443,
    login=user, 
    password=upg_key
)

saas_ops_connection = odoolib.get_connection(
    hostname="saas-ops.odoo.com",
    database="trantor_ops",
    protocol="jsonrpcs",
    port=443,
    login=user, 
    password=saas_ops_key
)

task_model = connection.get_model("project.task")
db_model = connection.get_model("openerp.enterprise.database")
upgrade_model = upg_connection.get_model("upgrade.request")
meta_upg_model = saas_ops_connection.get_model("meta.database.migration.report")

task_ids = task_model.search_read(
    [
        '&',
        '&',
        ("project_id", "=", UPGRADE_ISSUES_PROJECT_ID),
        ("stage_id", 'in', [TASK_STAGE_CODE_REVIEW_ID,
                            TASK_STAGE_ASSESSMENT_ID,
                            TASK_STAGE_TECHNICAL_ID,
                            TASK_STAGE_FUNCTIONAL_ID,
                            TASK_STAGE_READY_FOR_TECHNICAL_ID,
                            TASK_STAGE_READY_FOR_FUNCTIONAL_ID,
                            TASK_STAGE_INTERNAL_FEEDBACK_ID,
                            TASK_STAGE_CUSTOMER_FEEDBACK_ID]
        ),
        ('name', 'like', '[rr] '),
    ],
    ['name', 'stage_id', 'id'],
)
db_names = [task['name'].split()[1] for task in task_ids]
dbs = db_model.search_read([("db_name", "in", db_names), ("last_ping", ">", (datetime.now() - timedelta(days=31)).strftime("%Y-%m-%d") ), ('hosting', '=', 'saas')], ["db_name", "version", "db_uuid"])
db_vals = { db['db_name']: db for db in dbs }
rr_to_check = {}

for task in task_ids:
    db_name = task['name'].split()[1]
    db = db_vals.get(db_name, False)
    if not db:
        msg = f"Database {db_name} doesn't looks like alive anymore. Task is then cancelled."
        if debug:
            print(msg)
        else:
            task_model.message_post(task['id'], body=msg, message_type="comment")
            task_model.write(task['id'], {'stage_id': TASK_STAGE_CANCELLED_ID})
    elif db['version'].replace('+e', '') in valid_targets:
        msg = f"Database {db_name} is now in a supported version ({db['version']}), and this task can be closed."
        if debug:
            print(msg)
        else:
            task_model.message_post(task['id'], body=msg, message_type="comment")
            task_model.write(task['id'], {'stage_id': TASK_STAGE_DONE_ID})
    else:
        rr_to_check[db_name] = {'uuid': db['db_uuid'], 'stage_id': task['stage_id'][0], 'task_id': task['id'], 'version': db['version']}

# Update rr status with Metabase data
names_to_check = [rr for rr in rr_to_check.keys()]
meta_upg = meta_upg_model.search_read([('name', 'in', names_to_check)], ['name', 'rr_locked_until', 'preflight_state', 'preflight_version'])
for db in meta_upg:
    rr_to_check[db['name']].update(db)

# Check ticket VS Metabase data
for check in rr_to_check:
    db = rr_to_check[check]
    if not db.get('preflight_state', False):
        msg = f"DB {check} not found in Metabase or no existing preflight. Check subscription."
        # Too much errors on this one, do not trigger
        # print(msg)
        #task_model.message_post(db['task_id'], body=msg, message_type="comment")
    elif db['preflight_state'] in ('rolling_release_available', 'rolling_release_warning') and db['stage_id'] not in (TASK_STAGE_INTERNAL_FEEDBACK_ID, TASK_STAGE_CUSTOMER_FEEDBACK_ID, TASK_STAGE_DONE_ID):
        msg = f"DB {check} is ready for RR ({db['version']}->{db['preflight_version']}),"
        if db['rr_locked_until'] and db['rr_locked_until'] > datetime.now().strftime('%Y-%m-%d %H:%M:%S'):
            msg += " but it's locked until "
            msg += db['rr_locked_until']
        else:
            msg += " can be automatically upgraded"
        if debug:
            print(msg)
        else:
            task_model.message_post(db['task_id'], body=msg, message_type="comment")
            task_model.write(db['task_id'], {'stage_id': TASK_STAGE_INTERNAL_FEEDBACK_ID})
    elif db['preflight_state'] not in ('rolling_release_available', 'rolling_release_warning') and db['stage_id'] in (TASK_STAGE_INTERNAL_FEEDBACK_ID, TASK_STAGE_CUSTOMER_FEEDBACK_ID):
        msg = f"DB {check} is not ready for RR, preflight state is {db['preflight_state']}, while task is waiting feedback"
        #Check last preflight upgrade status
        lst_upg = upgrade_model.search_read([("db_uuid", "=", db['uuid']), ('quiet', '=', True), ('actuator', '=', 'meta'), ('aim', '=', 'test'), '|', ('active', '=', True), ('active', '=', False)], ["state", "id", "disabled_view_count", "create_date"], order="id desc", limit=1)
        if not lst_upg:
            msg = f"No automatic test upgrade found for {check} / {db['uuid']}. Please check subscription."
            print(msg)
            #task_model.message_post(db['task_id'], body=msg, message_type="comment")
            #task_model.write(db['task_id'], {'stage_id': TASK_STAGE_FUNCTIONAL_ID})

        elif lst_upg[0]['create_date']<(datetime.now()-timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S'):
            print(f"Test for db {db['name']} is too old, can't change anything.")

        elif lst_upg[0]['state'] in ('done', 'failed'):
            if lst_upg[0]['state'] == 'done':
                msg += f"\r\n \r\n Last automatic test upgrade was successful, but {lst_upg[0]['disabled_view_count']} views had been disabled during upgrade."
            elif lst_upg[0]['state'] == 'failed':
                msg += f"\r\n \r\n Last automatic test upgrade failed. Please check logs for more information"
            msg += f"\r\n \r\n Last automatic test url: https://upgrade.odoo.com/web#id={lst_upg[0]['id']}&menu_id=107&cids=1&action=150&model=upgrade.request&view_type=form"
            if debug:
                print(msg)
            else:
                task_model.message_post(db['task_id'], body=msg, message_type="comment")
                task_model.write(db['task_id'], {'stage_id': TASK_STAGE_TECHNICAL_ID})
