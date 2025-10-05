import frappe


@frappe.whitelist()
def create_floor_unit_log(self):
    log= frappe.new_doc("Floor Unit Log")
    log.floor_unit = self.name
    log.floor_unit_name = self.floor_unit_name
    log.floor = self.floor
    log.space = self.space
    log.property = self.property
    log.company = self.company
    log.ref_doc = self.ref_doc
    log.tenant= self.tenant
    log.rent_space = self.rent_space
    log.free_space = self.free_space
    log.disabled = self.disabled

    log.insert(ignore_permissions=True)
    log.submit()
    
@frappe.whitelist()
def create_log(self):
    log = frappe.new_doc("Lease Contract Log")
    log.lease_contract = self.name
    log.tenant_lessee = self.tenant_lessee
    log.lease_start = self.lease_start
    log.lease_end = self.lease_end
    log.docstatus = getattr(self, "docstatus", 0)
    log.status = getattr(self, "status", "")
    if self.rent_details and len(self.rent_details) > 0:
        for rent_row in self.rent_details:
            log.append("rent_details", {
                "rent_item": rent_row.rent_item,
                "floor_unit": rent_row.floor_unit,
                "area_square_meter": getattr(rent_row, 'area_square_meter', ''),
                "rate": rent_row.rate,
                "amount": rent_row.amount
            })

    log.insert(ignore_permissions=True)
    log.submit()