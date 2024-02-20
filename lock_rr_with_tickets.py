#!/usr/bin/env python3
from datetime import datetime, timedelta
import odoolib
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
user = config['CREDENTIALS']['login']
odoo_key = config['CREDENTIALS']['odoo_key']

UPGRADE_ISSUES_PROJECT_ID = 70

TASK_STAGE_CODE_REVIEW_ID = 25373
TASK_STAGE_ASSESSMENT_ID = 25372
TASK_STAGE_INTERNAL_FEEDBACK_ID = 152
TASK_STAGE_TECHNICAL_ID = 150
TASK_STAGE_READY_FOR_TECHNICAL_ID = 25525
TASK_STAGE_NEW_ID = 308
TASK_STAGE_CUSTOMER_FEEDBACK_ID = 32059

DB_SPLIT_SIZE = 100

connection = odoolib.get_connection(
    hostname="www.odoo.com",
    database="openerp",
    protocol="jsonrpcs",
    port=443,
    login=user, 
    password=odoo_key
)

task_model = connection.get_model("project.task")
db_model = connection.get_model("openerp.enterprise.database")

task_nbr = task_model.search_count(
    [
        '&', 
        '&', 
        ("project_id", "=", UPGRADE_ISSUES_PROJECT_ID), 
        ("stage_id", 'in', [TASK_STAGE_CODE_REVIEW_ID, 
                            TASK_STAGE_ASSESSMENT_ID, 
                            TASK_STAGE_INTERNAL_FEEDBACK_ID, 
                            TASK_STAGE_TECHNICAL_ID, 
                            TASK_STAGE_READY_FOR_TECHNICAL_ID, 
                            TASK_STAGE_NEW_ID, 
                            TASK_STAGE_CUSTOMER_FEEDBACK_ID]
        ),
        ('mnt_subscription_id', '=', False)
    ],
)
print("%s tickets without subs in process" % task_nbr)

task_ids = task_model.search_read(
    [
        '&', 
        '&', 
        ("project_id", "=", UPGRADE_ISSUES_PROJECT_ID), 
        ("stage_id", 'in', [TASK_STAGE_CODE_REVIEW_ID, 
                            TASK_STAGE_ASSESSMENT_ID, 
                            TASK_STAGE_INTERNAL_FEEDBACK_ID, 
                            TASK_STAGE_TECHNICAL_ID, 
                            TASK_STAGE_READY_FOR_TECHNICAL_ID, 
                            TASK_STAGE_NEW_ID, 
                            TASK_STAGE_CUSTOMER_FEEDBACK_ID]
        ),
        ('mnt_subscription_id', '!=', False)
    ],
    ['mnt_subscription_id', 'date_deadline'],
)
sub_ids = list(set([t['mnt_subscription_id'][0] for t in task_ids]))
ddl = {t['mnt_subscription_id'][0]: t['date_deadline'] for t in task_ids}
print("%s tickets with subs in process" % len(sub_ids))

i=0
while (i<len(sub_ids)):
    tmp_sub_ids = sub_ids[i: i+DB_SPLIT_SIZE]
    db_ids = db_model.read_group(
        ['&', ("subscription_id", "in", tmp_sub_ids), ("hosting", '=', 'saas')],
        ['subscription_id', 'name:min(db_name)'],
        ['subscription_id']
    )
    for db in db_ids:
        if db['subscription_id_count']>1:
            print("Too much DB for contract %s: %s dbs" % (db['subscription_id'][1], db['subscription_id_count']))
        else:
            sub_id = db['subscription_id'][0]
            deadline = ddl[sub_id] or (datetime.now() + timedelta(days=5)).isoformat()
            if datetime.fromisoformat(deadline)>datetime.now() + timedelta(days=30):
                deadline = (datetime.now() + timedelta(days=30)).isoformat()
            print("Lock db %s up to %s" % (db['name'], deadline))

    i+=DB_SPLIT_SIZE
