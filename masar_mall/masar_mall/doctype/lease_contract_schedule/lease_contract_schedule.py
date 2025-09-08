# Copyright (c) 2025, KCSC and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class LeaseContractSchedule(Document):
	pass

def on_submit(self):
    lease_doc = frappe.get_doc("Lease Contract", self.lease_contract)
    # Create Sales Invoice only for non-allowance months
    invoice = frappe.new_doc("Sales Invoice")
    invoice.customer = lease_doc.tenant_lessee

    if invoice.meta.has_field("lease_contract"):
        invoice.lease_contract = lease_doc.name

    for row in self.invoice:
        if not getattr(row, "is_allowance", 0):
            invoice.append("items", {
                "item_code": row.rent_item if hasattr(row, "rent_item") else "",
                "description": f"Lease payment for {row.lease_start} to {row.lease_end}",
                "qty": 1,
                "rate": row.amount,
            })

    invoice.insert(ignore_permissions=True)
    invoice.submit()

    # Update child table with invoice number and status
    for row in self.invoice:
        if not getattr(row, "is_allowance", 0):
            row.invoice_number = invoice.name
            row.invoice_status = invoice.status

    self.save(ignore_permissions=True)
