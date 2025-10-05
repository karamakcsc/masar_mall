# Copyright (c) 2025, KCSC and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import time


class Floor(Document):

    def on_submit(self):


        warehouse_name = frappe.db.get_value(
            "Warehouse",
            {"warehouse_name": self.name, "company": self.company},
            "name"
        )

        if not warehouse_name:
            stock_account = frappe.db.get_value(
                "Account",
                {"account_type": "Stock", "company": self.company},
                "name"
            )
            if not stock_account:
                frappe.throw(f"No Stock Account found for company '{self.company}'.")

            warehouse = frappe.get_doc({
                "doctype": "Warehouse",
                "warehouse_name": self.name,
                "company": self.company,
                "address_line_1": self.address or "",
                "parent_warehouse": self.parent_wh,
                "warehouse_type": "Space",
                "is_group": 0,
                "account": stock_account,
            })
            warehouse.insert(ignore_permissions=True)
            warehouse_name = warehouse.name

     
        self.db_set("wh_name", warehouse_name)

   
        item_code = frappe.get_value("Item", {"is_stock_item": 1, "custom_rent_space": 1}, "name")
        if not item_code:
            frappe.throw("No stock item with Rent Space enabled was found. Please create or update an Item.")
   
        expense_account = frappe.db.get_value("Account", {"account_type": "Temporary", "company": self.company},"name")
        if not expense_account:
       
            expense_account = frappe.db.get_value(
                "Account",
                {"account_type": "Stock Adjustment", "company": self.company},
                "name"
            )
        if not expense_account:
            frappe.throw(f"No valid Expense Account found for company '{self.company}'.")

        st_rec = frappe.get_doc({
            "doctype": "Stock Reconciliation",
            "set_warehouse": warehouse_name,
            "company": self.company,
            "purpose": "Stock Reconciliation",
            "posting_date": self.date or frappe.utils.nowdate(),
            "posting_time": time(0, 0, 0),
            "set_posting_time": 1,
            "expense_account": expense_account,
            "items": [
                {
                    "item_code": item_code,
                    "qty": self.space,
                    "valuation_rate": 1,
                    "warehouse": warehouse_name
                }
            ]
        })
        st_rec.insert(ignore_permissions=True)
        st_rec.submit()

        self.db_set("ref_doc", st_rec.name)