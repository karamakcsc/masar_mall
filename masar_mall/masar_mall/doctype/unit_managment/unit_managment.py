# Copyright (c) 2025, KCSC and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import time


class UnitManagment(Document):

    def on_submit(self):
        wh_ta = frappe.db.get_value("Warehouse", {"warehouse_type": "Rental Space"}, "name")
        item_name = frappe.db.get_value("Item", {"is_stock_item": 1}, "name")
       
        if not item_name:
            frappe.throw("No stock item found to process transaction.")

        item = frappe.get_doc("Item", item_name)

        if self.action_type == 'Rent Space':
            fr_unt = frappe.get_doc({
                "doctype": "Floor Unit",
                "unit_name": self.floor_unit,
                "company": self.company,
                "rent_space": 1,
                "property": self.property,
                "floor": self.floor,
                "area": self.area
            })
            fr_unt.insert(ignore_permissions=True)
            fr_unt.save()
            fr_unt.submit()
            self.db_set("ref_doc", fr_unt.name)
            frappe.msgprint(f"Floor Unit '{self.name}' created.")

        elif self.action_type == 'Return Space':
            st_ent = frappe.get_doc({
                "doctype": "Stock Entry",
                "stock_entry_type": "Material Transfer",
                "from_warehouse": wh_ta,
                "to_warehouse": self.wh_name,
                "company": self.company,
                "posting_date": self.date,
                "items": [
                    {
                        "item_code": item.name,
                        "qty": self.exit_area,
                        "floor_unit": self.exit_floor_unit,
                        "to_floor_unit": self.exit_floor_unit,
                    }
                ]
            })
            st_ent.insert(ignore_permissions=True)
            st_ent.submit()
            self.db_set("ref_doc", st_ent.name)
            if self.exit_floor_unit:
                exit_floor_unit_doc = frappe.get_doc("Floor Unit", self.exit_floor_unit)
                exit_floor_unit_doc.db_set("return_space", 1)
            frappe.msgprint(f"Floor Unit '{self.name}'  Returned Space.")