#!/usr/bin/env python3
import odoolib
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
user = config['CREDENTIALS']['login']
odoo_key = config['CREDENTIALS']['odoo_key']

connection = odoolib.get_connection(
    hostname="www.odoo.com",
    database="openerp",
    protocol="jsonrpcs",
    port=443,
    login=user, 
    password=odoo_key
)

db_list = """

"""

task_model = connection.get_model("project.task")
for db in db_list.split():
    print(db)
    task_id = task_model.create({
        "analytic_account_id": 351,
        "company_id": 1,
        "date_deadline": False,
        "description": f"""
        <p>This is an <b>internal ticket</b>, customer is not involved</p>
        <p>Rolling release to 17.0 failed, either because of traceback during upgrade or deactivated views.</p>
        <p>If the request is archived :<br/> 
<br/>
1) connect to the support page of the database : <a href="https://{db}.odoo.com/_odoo/support">https://{db}.odoo.com/_odoo/support</a><br/>
<br/>
2) In the migration request section : <br/>
<br/>
Mode = Test <br/>
Target = select the appropriate target based on the last requests. <br/>
Email : your email address<br/>
<br/>
3) Click on queue request. <br/>
<br/>
Demo : <a href="https://drive.google.com/file/d/1CPT8SOCHecw2VYu4W1Nr4XO_OImNkiTY/view">https://drive.google.com/file/d/1CPT8SOCHecw2VYu4W1Nr4XO_OImNkiTY/view</a>
<br/>
<br/>
Note : <br/>
<br/>
If no subscription number is linked to the DB. <br/>
<br/>
Search the database in Subscription > Databases 
Use the UUID to search for the Upgrade Request.</p>   
        """,
        # "kanban_state": "normal",
        "name": f"[rr] {db}",
        "project_id": 70,
        # "stage_id": 308,
        "stage_id": 25525,
        "tag_ids": [[6, 0, [25106, ]]],
        "user_ids": [[6, 0, [ ]]],
    })
    print(task_id)

# Nombre de vues desactivees
# numero de la sub

