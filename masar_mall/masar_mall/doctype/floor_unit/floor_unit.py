# Copyright (c) 2025, KCSC and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from masar_mall.utils.create_log import create_floor_unit_log


class FloorUnit(Document):
    def on_submit(self):
        self.create_stock_entry()
        create_floor_unit_log(self)
    def on_update(self):
        self.update_tenant_se()

    def create_stock_entry(self):
        wh_ta = frappe.db.get_value("Warehouse", {"warehouse_type": "Rental Space"}, "name")
        item_code = frappe.get_value("Item", {"is_stock_item": 1, "custom_rent_space": 1}, "name")

        if not item_code:
            frappe.throw("No stock item with Rent Space enabled was found. Please create or update an Item.")
            
        st = frappe.get_doc({
            "doctype": "Stock Entry",
            "stock_entry_type": "Material Transfer",
            "from_warehouse": self.floor_wh,
            "to_warehouse": wh_ta,
            "company": self.company,
            "posting_date": self.date,
            "custom_ref_doc": self.name,
            "items": [
                {
                    "item_code": item_code,
                    "qty": self.space,
                    "floor_unit": self.name,
                    "s_warehouse": self.floor_wh,
                    "t_warehouse": wh_ta,
                    "to_floor_unit": self.name,
                    "tenant": self.tenant if self.tenant else None
                }
            ]
        })

        st.insert(ignore_permissions=True)
        st.submit()
        self.ref_doc = st.name

    def update_tenant_se(self):
        if self.ref_doc and self.tenant:
            frappe.db.sql("""
                UPDATE `tabStock Entry Detail`
                SET tenant = %s
                WHERE parent = %s
            """, (self.tenant, self.ref_doc))
            frappe.db.commit()
    
    @frappe.whitelist()
    def disable_unit(self):
        lc_sql = frappe.db.sql("""
            SELECT parent 
            FROM `tabLease Contract Details`
            WHERE floor_unit = %s AND docstatus = 1
        """, (self.name,), as_dict=True)
        
        if lc_sql:
            frappe.throw(
                f"Cannot disable Floor Unit <b>{self.name}</b> because it is linked to an active Lease Contract <b>{lc_sql[0].parent}</b>."
            )

        self.reverse_stock_entries()
        
        frappe.db.set_value(self.doctype, self.name, "disabled", 1)
        frappe.db.commit()
        
        self.reload()
        
        create_floor_unit_log(self)
        
        frappe.msgprint(f"Floor Unit <b>{self.name}</b> has been disabled successfully.", alert=True, indicator="orange")
        return True
    
    def reverse_stock_entries(self):
        se_sql = frappe.db.sql("""
            SELECT parent
            FROM `tabStock Entry Detail`
            WHERE floor_unit = %s AND docstatus = 1
        """, (self.name,), as_dict=True)
        
        if se_sql:
            for row in se_sql:
                stock_entry = frappe.get_doc("Stock Entry", row.parent)
                reversal = frappe.new_doc("Stock Entry")
                reversal.stock_entry_type = "Material Transfer"
                reversal.purpose = stock_entry.purpose
                reversal.from_warehouse = stock_entry.to_warehouse
                reversal.to_warehouse = stock_entry.from_warehouse
                reversal.custom_ref_doc = self.name
                
                for item in stock_entry.items:
                    reversal.append("items", {
                        "item_code": item.item_code,
                        "qty": item.qty,
                        "uom": item.uom,
                        "stock_uom": item.stock_uom,
                        "conversion_factor": item.conversion_factor,
                        "floor_unit": item.floor_unit,
                        "s_warehouse": item.t_warehouse,
                        "t_warehouse": item.s_warehouse
                    })

                reversal.insert(ignore_permissions=True)
                reversal.submit()

                frappe.msgprint(
                    f"Reversal Stock Entry <b>{reversal.name}</b> created for {row.parent}", 
                    alert=True, 
                    indicator="green"
                )
    
    @frappe.whitelist()
    def release_from_lease(self):
        self.reverse_stock_entries()
        
        frappe.db.set_value(self.doctype, self.name, "rent_space", 0)
        frappe.db.set_value(self.doctype, self.name, "free_space", 1)
        frappe.db.set_value(self.doctype, self.name, "tenant", None)
        frappe.db.commit()
        
        self.reload()
        
        create_floor_unit_log(self)
        
        return True