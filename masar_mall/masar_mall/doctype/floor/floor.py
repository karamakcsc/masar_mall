# Copyright (c) 2025, KCSC and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Floor(Document):

    def on_submit(self):
        acc = frappe.db.get_value("Account", {"account_type": "Stock"}, "name")
        if not frappe.db.exists("Warehouse", self.name):
            warehouse = frappe.get_doc({
                "doctype": "Warehouse",
                "warehouse_name": self.name,
                "company": self.company,
                "address_line_1": self.address,
                "parent_warehouse": self.parent_wh,
                "warehouse_type": "Space",
                "is_group": 0,
                "account": acc,
            })
            warehouse.insert(ignore_permissions=True)
            self.db_set("wh_name", warehouse.name)
            frappe.msgprint(f"Floor '{self.name}' created successfully.")
        else:
            self.db_set("wh_name", warehouse.name)
            frappe.msgprint(f"Floor '{self.name}' already exists.")