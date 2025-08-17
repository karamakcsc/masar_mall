# Copyright (c) 2025, KCSC and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class UnitManagment(Document):

    def on_submit(self):
        wh_ta = frappe.db.get_value("Warehouse", {"warehouse_type": "Rental Space"}, "name")
        item_code = frappe.get_value("Item", {"is_stock_item": 1, "custom_rent_space": 1}, "name")
        if not item_code:
            frappe.throw("No stock item with Rent Space enabled was found. Please create or update an Item.")

        item = frappe.get_doc("Item", item_code)

        # Rent Space New Floor Unit
        if self.action_type == 'Rent Space' and self.is_new_floor_unit:
            fr_new_unit = frappe.get_doc({
                "doctype": "Floor Unit",
                "unit_name": self.new_floor_unit,
                "company": self.company,
                "rent_space": 1,
                "property": self.property,
                "floor": self.floor,
                "area": self.new_area
            })
            fr_new_unit.insert(ignore_permissions=True)
            fr_new_unit.submit()

            self.db_set("ref_doc", fr_new_unit.name)
            frappe.msgprint(f"Floor Unit '{fr_new_unit.name}' created and submitted.")

        # Rent Space is Exist Floor Unit
        elif self.action_type == 'Rent Space' and self.is_existing:
            stock_in = frappe.get_doc({
                "doctype": "Stock Entry",
                "stock_entry_type": "Material Transfer",
                "from_warehouse": wh_ta,
                "to_warehouse": self.rent_exist_wh_name,
                "company": self.company,
                "posting_date": self.date,
                "items": [
                    {
                        "item_code": item.name,
                        "qty": self.rent_exist_area,
                        "floor_unit": self.return_exit_unit,
                        "to_floor_unit": self.return_exit_unit,
                    }
                ]
            })
            stock_in.insert(ignore_permissions=True)
            stock_in.submit()
            self.db_set("ref_doc_return", stock_in.name)

         # Move new Area
            stock_out = frappe.get_doc({
                "doctype": "Stock Entry",
                "stock_entry_type": "Material Transfer",
                "from_warehouse": self.rent_exist_wh_name,
                "to_warehouse": wh_ta,
                "company": self.company,
                "posting_date": self.date,
                "items": [
                    {
                        "item_code": item.name,
                        "qty": self.new_area,
                        "floor_unit": self.return_exit_unit,
                        "to_floor_unit": self.return_exit_unit,
                    }
                ]
            })
            stock_out.insert(ignore_permissions=True)
            stock_out.submit()
            self.db_set("ref_doc", stock_out.name)

            # floor unit is returned
            if self.return_exit_unit:
                return_exit_unit_doc = frappe.get_doc("Floor Unit", self.return_exit_unit)
                return_exit_unit_doc.db_set("return_space", 1)

            frappe.msgprint(f"Floor Unit '{self.return_exit_unit}' updated as Returned Space.")

        # Return Space
        elif self.action_type == 'Return Space':
            st_ent = frappe.get_doc({
                "doctype": "Stock Entry",
                "stock_entry_type": "Material Transfer",
                "from_warehouse": wh_ta,
                "to_warehouse": self.return_wh_name,
                "company": self.company,
                "posting_date": self.date,
                "items": [
                    {
                        "item_code": item.name,
                        "qty": self.exit_area,
                        "floor_unit": self.return_exit_unit,
                        "to_floor_unit": self.return_exit_unit,
                    }
                ]
            })
            st_ent.insert(ignore_permissions=True)
            st_ent.submit()
            self.db_set("ref_doc", st_ent.name)

            # is returned unit
            if self.return_exit_unit:
                return_exit_unit_doc = frappe.get_doc("Floor Unit", self.return_exit_unit)
                return_exit_unit_doc.db_set("return_space", 1)

            frappe.msgprint(f"Floor Unit '{self.return_exit_unit}' marked as Returned Space.")
