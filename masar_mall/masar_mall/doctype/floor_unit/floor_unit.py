# # Copyright (c) 2025, KCSC and contributors
# # For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cint


class FloorUnit(Document):
    def create_stock_entry(self, from_wh, to_wh, item, action="enabled"):
        """Helper function to create a stock entry for this Floor Unit"""
        st = frappe.get_doc({
            "doctype": "Stock Entry",
            "stock_entry_type": "Material Transfer",
            "from_warehouse": from_wh,
            "to_warehouse": to_wh,
            "company": self.company,
            "posting_date": self.date,
            "custom_ref_doc": self.name,
            "items": [
                {
                    "item_code": item.name,
                    "qty": self.space,
                    "floor_unit": self.name,
                    "s_warehouse": from_wh,
                    "t_warehouse": to_wh,
                    "to_floor_unit": self.name,
                    "tenant": self.tenant if self.tenant else None
                }
            ]
        })

        st.insert(ignore_permissions=True)
        st.submit()

        # Update reference fields
        self.db_set("ref_doc", st.name)

        if action == "enabled" and self.tenant:
            self.db_set("rent_space", 1)
        elif action == "disabled":
            self.db_set("rent_space", 0)

        return st

    def on_submit(self):
        wh_ta = frappe.db.get_value("Warehouse", {"warehouse_type": "Rental Space"}, "name")
        item_code = frappe.get_value("Item", {"is_stock_item": 1, "custom_rent_space": 1}, "name")

        if not item_code:
            frappe.throw("No stock item with Rent Space enabled was found. Please create or update an Item.")

        item = frappe.get_doc("Item", item_code)

        # Always enable stock on first submit
        self.create_stock_entry(self.floor_wh, wh_ta, item, action="enabled")

        frappe.msgprint(f"Floor Unit '{self.name}' created and submitted.")

        create_floor_unit_log(self)

    def on_update(self):
        # Update tenant in Stock Entry if tenant field is changed
        if self.ref_doc and self.tenant:
            frappe.db.sql("""
                UPDATE `tabStock Entry Detail`
                SET tenant = %s
                WHERE parent = %s
            """, (self.tenant, self.ref_doc))
            frappe.db.commit()
            frappe.msgprint(_("Tenant updated successfully in Stock Entry {0}").format(self.ref_doc))

    def on_update_after_submit(self):
        wh_ta = frappe.db.get_value("Warehouse", {"warehouse_type": "Rental Space"}, "name")
        item_code = frappe.get_value("Item", {"is_stock_item": 1, "custom_rent_space": 1}, "name")

        if not item_code:
            frappe.throw("No stock item with Rent Space enabled was found. Please create or update an Item.")

        item = frappe.get_doc("Item", item_code)

        disable_flag = cint(self.disable)

        if disable_flag:
            # Disable floor unit: move stock back to floor warehouse
            self.create_stock_entry(wh_ta, self.floor_wh, item, action="disabled")
            frappe.msgprint(f"Floor Unit '{self.name}' disabled and stock returned.")
        else:
            # Enable floor unit: move stock into rental warehouse
            self.create_stock_entry(self.floor_wh, wh_ta, item, action="enabled")
            frappe.msgprint(f"Floor Unit '{self.name}' enabled and stock moved to rental space.")


@frappe.whitelist()
def st_update(name, tenant):
    if not name:
        frappe.throw(_("Stock Entry name is required."))

    if not frappe.db.exists("Stock Entry", name):
        frappe.throw(_("Stock Entry {0} does not exist").format(name))

    frappe.db.sql("""
        UPDATE `tabStock Entry Detail`
        SET tenant = %s
        WHERE parent = %s
    """, (tenant, name))

    frappe.db.commit()
    frappe.msgprint(_("Tenant updated successfully in Stock Entry {0}").format(name))


@frappe.whitelist()
def st_disable_floor_unit(floor_unit_name):
    # Get the full Floor Unit document
    floor_unit = frappe.get_doc("Floor Unit", floor_unit_name)

    wh_ta = frappe.db.get_value("Warehouse", {"warehouse_type": "Rental Space"}, "name")
    item_code = frappe.get_value("Item", {"is_stock_item": 1, "custom_rent_space": 1}, "name")

    if not item_code:
        frappe.throw("No stock item with Rent Space enabled was found. Please create or update an Item.")

    item = frappe.get_doc("Item", item_code)

    floor_unit.create_stock_entry(wh_ta, floor_unit.floor_wh, item, action="disabled")
    floor_unit.db_set("disable", 1)

    frappe.msgprint(f"Floor Unit '{floor_unit.name}' disabled successfully.")

def create_floor_unit_log(self):
    log= frappe.new_doc("Floor Unit Log")
    log.floor_unit = self.name
    log.floor = self.floor
    log.space = self.space
    log.property = self.property
    log.company = self.company
    log.action_type= "Rent Space" if self.rent_space == 1 else "Disabled"

    log.insert(ignore_permissions=True)
    frappe.msgprint(f"Floor Unit Log for '{self.name}' created successfully.")