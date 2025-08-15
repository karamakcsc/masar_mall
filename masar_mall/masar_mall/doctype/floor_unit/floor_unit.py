# # Copyright (c) 2025, KCSC and contributors
# # For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import time

class FloorUnit(Document):

    def on_submit(self):
        wh_ta = frappe.db.get_value("Warehouse", {"warehouse_type": "Rental Space"}, "name")
        acc_tem = frappe.db.get_value("Account", {"account_type": "Temporary"}, "name")
        item_name = frappe.db.get_value("Item", {"is_stock_item": 1}, "name")

        if not item_name:
            frappe.throw("No stock item found to process transaction.")

        item = frappe.get_doc("Item", item_name)

        if self.whole_space:
            st_rec = frappe.get_doc({
                "doctype": "Stock Reconciliation",
                "set_warehouse": self.wh_name,
                "company": self.company,
                "purpose": "Stock Reconciliation",
                "posting_date": self.date,
                "posting_time": time(0, 0, 0),
                "set_posting_time": 1,
                "expense_account": acc_tem,
                "items": [
                    {
                        "item_code": item.name,
                        "qty": self.area,
                        "valuation_rate": 1,
                        "warehouse": self.wh_name
                    }
                ]
            })
            st_rec.insert(ignore_permissions=True)
            st_rec.submit()
            self.db_set("ref_doc", st_rec.name)
            frappe.msgprint(f"Floor Unit '{self.name}' created.")

        else:
            st_ent = frappe.get_doc({
                "doctype": "Stock Entry",
                "stock_entry_type": "Material Transfer",
                "from_warehouse": self.wh_name,
                "to_warehouse": wh_ta,
                "company": self.company,
                "posting_date": self.date,
                "items": [
                    {
                        "item_code": item.name,
                        "qty": self.area
                    }
                ]
            })
            st_ent.insert(ignore_permissions=True)
            st_ent.submit()
            self.db_set("ref_doc", st_ent.name)
            frappe.msgprint(f"Floor Unit '{self.name}'  Rental Space.")