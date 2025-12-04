# # Copyright (c) 2025, KCSC and contributors
# # For license information, please see license.txt

# import frappe
# from frappe.utils import getdate, nowdate, flt, rounded

# def check_lease_end_and_create_invoice():
#     today = getdate(nowdate())

#     leases = frappe.get_all(
#         "Lease Contract",
#         filters={
#             "status": "Rent",
#             "docstatus": 1,
#         },
#         fields=["name", "lease_end"]
#     )
#     if not leases:
#         frappe.throw("No active Lease Contracts found.")

#     for lease in leases:
#         if lease.lease_end and today > getdate(lease.lease_end):
#             continue

#         lease_doc = frappe.get_doc("Lease Contract", lease.name)
#         company_doc = frappe.get_doc("Company", lease_doc.owner_lessor)
#         schedules = frappe.get_all(
#             "Lease Contract Schedule",
#             filters={"lease_contract": lease_doc.name, "docstatus": 1},
#             fields=["name"]
#         )
#         if not schedules:
#             frappe.throw(f"No schedules found for Lease Contract {lease_doc.name}")

#         for sched in schedules:
#             schedule_doc = frappe.get_doc("Lease Contract Schedule", sched.name)
            
#             for row in schedule_doc.invoice:
                
#                 if row.is_allowance:
#                     continue
                
#                 if row.invoice_number:
#                     continue
                
#                 row_start_date = getdate(row.lease_start)
#                 if row_start_date > today:
#                     continue
                
#                 if not lease_doc.contract_multi_period:
#                     create_individual_invoice(lease_doc, row, schedule_doc)
#                 elif lease_doc.contract_multi_period:
#                     create_multi_period_invoices(lease_doc, row, schedule_doc)
                
#         if lease_doc.other_service:
#             for service in lease_doc.other_service:
#                 if service.invoice_number:
#                     continue
#                 if service.invoice_date and service.invoice_date <= today:
#                     invoice = frappe.new_doc("Sales Invoice")
#                     invoice.customer = lease_doc.tenant_lessee
#                     posting_date = service.invoice_date
#                     due_date = service.invoice_date
#                     invoice.set_posting_time = 1
#                     invoice.posting_date = str(posting_date)
#                     invoice.due_date = str(due_date)
#                     invoice.custom_lease_contract = lease_doc.name
#                     invoice.debit_to = company_doc.default_receivable_account if company_doc.default_receivable_account else frappe.throw(f"Please set Default Receivable Account in Company Settings")
#                     item_doc = frappe.get_doc("Item", service.service_item)

#                     service_rate = rounded(flt(service.rate), 6)
                    
#                     invoice.append("items", {
#                         "item_code": service.service_item,
#                         "item_name": service.item_name or item_doc.item_name,
#                         "item_group": item_doc.item_group,
#                         "qty": 1,
#                         "rate": service_rate,
#                         "amount": service_rate,
#                         "uom": item_doc.stock_uom,
#                         "income_account": (
#                             company_doc.default_income_account
#                             if company_doc.default_income_account
#                             else frappe.throw("Please set Default Income Account in Company Settings")
#                         ),
#                         "enable_deferred_revenue": 1 if posting_date != due_date else 0,
#                         "service_start_date": posting_date,
#                         "service_end_date": due_date,
#                     })

#                     # invoice.run_method("set_taxes")

#                     invoice.save(ignore_permissions=True)
#                     invoice.submit()
#                     service.invoice_number = invoice.name
#                     service.db_update()
                

# def create_individual_invoice(lease_doc, payment_row, schedule_doc):
#     try:
#         company_doc = frappe.get_doc("Company", lease_doc.owner_lessor)
#         if not lease_doc.tenant_lessee:
#             frappe.throw(f"Lease Contract {lease_doc.name} has no Tenant/Customer linked!")
#             return

#         invoice = frappe.new_doc("Sales Invoice")
#         invoice.customer = lease_doc.tenant_lessee

#         posting_date = payment_row.lease_start
#         due_date = payment_row.lease_end
#         invoice.set_posting_time = 1
#         invoice.posting_date = str(posting_date)
#         invoice.due_date = str(due_date)
#         invoice.custom_lease_contract = lease_doc.name
#         invoice.debit_to = company_doc.default_receivable_account if company_doc.default_receivable_account else frappe.throw(f"Please set Default Receivable Account in Company Settings")

#         item_codes = frappe.get_all("Lease Contract Details",
#             filters={
#                 "parent": lease_doc.name,
#             },
#             fields=["rent_item", "amount"]
#         )                
         
#         if not item_codes:
#             frappe.throw(f"No items found in Lease Contract {lease_doc.name} to create invoice.")

#         total_months = rounded(flt(getattr(lease_doc, 'period_in_months', 0)) / flt(getattr(lease_doc, 'billing_frequency', 1)), 6)
#         if not lease_doc.contract_multi_period:
#             if lease_doc.allowance_period and lease_doc.in_period:
#                 total_months = rounded(total_months - flt(lease_doc.allowance_period), 6)
        
#         for item in item_codes:
#             item_doc = frappe.get_doc("Item", item.rent_item)
#             if not lease_doc.contract_multi_period:
#                 item_rate = rounded(flt(item.amount) / total_months, 6)
                
#                 invoice.append("items", {
#                     "item_code": item.rent_item,
#                     "item_name": item_doc.item_name,
#                     "item_group": item_doc.item_group,
#                     "qty": 1,
#                     "rate": item_rate,
#                     "uom": item_doc.stock_uom,
#                     "income_account": company_doc.default_income_account if company_doc.default_income_account else frappe.throw(f"Please set Default Income Account in Company Settings"),
#                     "enable_deferred_revenue": 1,
#                     "service_start_date": posting_date,
#                     "service_end_date": due_date,
#                 })
            
#         # invoice.run_method("set_taxes")

#         invoice.save(ignore_permissions=True)
#         invoice.submit()

#         frappe.msgprint(f"Sales Invoice {invoice.name} created for period {payment_row.lease_start} to {payment_row.lease_end}", alert=True, indicator="green")

#         payment_row.invoice_number = invoice.name
#         payment_row.invoice_status = invoice.status
#         schedule_doc.save(ignore_permissions=True)

#     except Exception as e:
#         frappe.throw(f"Failed to create invoice for payment period: {str(e)}")
        
# def create_multi_period_invoices(lease_doc, payment_row, schedule_doc):
#     try:
#         company_doc = frappe.get_doc("Company", lease_doc.owner_lessor)
#         if not lease_doc.tenant_lessee:
#             frappe.throw(f"Lease Contract {lease_doc.name} has no Tenant/Customer linked!")

#         invoice = frappe.new_doc("Sales Invoice")
#         invoice.customer = lease_doc.tenant_lessee

#         posting_date = payment_row.lease_start
#         due_date = payment_row.lease_end
#         invoice.set_posting_time = 1
#         invoice.posting_date = str(posting_date)
#         invoice.due_date = str(due_date)
#         invoice.custom_lease_contract = lease_doc.name
#         invoice.debit_to = company_doc.default_receivable_account or frappe.throw("Please set Default Receivable Account in Company Settings")

#         period = None
#         for p in lease_doc.period_details:
#             if getdate(p.from_date) <= getdate(posting_date) <= getdate(p.to_date):
#                 period = p
#                 break

#         if not period:
#             frappe.throw(f"No matching period detail found for posting date {posting_date} in Lease {lease_doc.name}")

#         period_months = flt(period.month_in_period)
#         if period_months <= 0:
#             frappe.throw("Invalid 'month_in_period' value in period details.")

#         if lease_doc.allowance_period and lease_doc.in_period and period == lease_doc.period_details[0]:
#             period_months = rounded(period_months - flt(lease_doc.allowance_period), 6)

#         service_rent_monthly = rounded(flt(period.service_amount) / period_months, 6)
#         space_rent_monthly = rounded(flt(period.space_amount) / period_months, 6)
        
#         for rent_item in lease_doc.rent_details:
#             item_doc = frappe.get_doc("Item", rent_item.rent_item)
#             monthly_rate = space_rent_monthly if rent_item.is_stock_item else service_rent_monthly
#             invoice_rate = rounded(monthly_rate * flt(lease_doc.billing_frequency), 6)

#             invoice.append("items", {
#                 "item_code": rent_item.rent_item,
#                 "item_name": item_doc.item_name,
#                 "item_group": item_doc.item_group,
#                 "qty": 1,
#                 "rate": invoice_rate,
#                 "uom": item_doc.stock_uom,
#                 "income_account": company_doc.default_income_account or frappe.throw("Please set Default Income Account in Company Settings"),
#                 "enable_deferred_revenue": 1,
#                 "service_start_date": posting_date,
#                 "service_end_date": due_date,
#             })

#         # invoice.run_method("set_taxes")

#         invoice.save(ignore_permissions=True)
#         invoice.submit()

#         payment_row.invoice_number = invoice.name
#         payment_row.invoice_status = invoice.status
#         schedule_doc.save(ignore_permissions=True)

#     except Exception as e:
#         frappe.throw(f"Failed to create multi-period invoice: {str(e)}")
# Copyright (c) 2025, KCSC and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, nowdate, flt, rounded

def check_lease_end_and_create_invoice():
    today = getdate(nowdate())

    leases = frappe.get_all(
        "Lease Contract",
        filters={
            "status": "Rent",
            "docstatus": 1,
        },
        fields=["name", "lease_end"]
    )
    if not leases:
        frappe.throw("No active Lease Contracts found.")

    for lease in leases:
        if lease.lease_end and today > getdate(lease.lease_end):
            continue

        lease_doc = frappe.get_doc("Lease Contract", lease.name)
        company_doc = frappe.get_doc("Company", lease_doc.owner_lessor)
        schedules = frappe.get_all(
            "Lease Contract Schedule",
            filters={"lease_contract": lease_doc.name, "docstatus": 1},
            fields=["name"]
        )
        if not schedules:
            frappe.throw(f"No schedules found for Lease Contract {lease_doc.name}")

        for sched in schedules:
            schedule_doc = frappe.get_doc("Lease Contract Schedule", sched.name)
            
            for row in schedule_doc.invoice:
                
                if row.is_allowance:
                    continue
                
                if row.invoice_number:
                    continue
                
                row_start_date = getdate(row.lease_start)
                if row_start_date > today:
                    continue
                
                if not lease_doc.contract_multi_period:
                    create_individual_invoice(lease_doc, row, schedule_doc)
                elif lease_doc.contract_multi_period:
                    create_multi_period_invoices(lease_doc, row, schedule_doc)
                
        if lease_doc.other_service:
            for service in lease_doc.other_service:
                if service.invoice_number:
                    continue
                if service.invoice_date and service.invoice_date <= today:
                    invoice = frappe.new_doc("Sales Invoice")
                    invoice.customer = lease_doc.tenant_lessee
                    posting_date = service.invoice_date
                    due_date = service.invoice_date
                    invoice.set_posting_time = 1
                    invoice.posting_date = str(posting_date)
                    invoice.due_date = str(due_date)
                    invoice.custom_lease_contract = lease_doc.name
                    invoice.debit_to = company_doc.default_receivable_account if company_doc.default_receivable_account else frappe.throw(f"Please set Default Receivable Account in Company Settings")
                    
                    # Get default taxes template from company or use a specific one for lease contracts
                    apply_taxes_template(invoice, lease_doc, company_doc)
                    
                    item_doc = frappe.get_doc("Item", service.service_item)
                    service_rate = rounded(flt(service.rate), 6)
                    
                    invoice.append("items", {
                        "item_code": service.service_item,
                        "item_name": service.item_name or item_doc.item_name,
                        "item_group": item_doc.item_group,
                        "qty": 1,
                        "rate": service_rate,
                        "amount": service_rate,
                        "uom": item_doc.stock_uom,
                        "income_account": (
                            company_doc.default_income_account
                            if company_doc.default_income_account
                            else frappe.throw("Please set Default Income Account in Company Settings")
                        ),
                        "enable_deferred_revenue": 1 if posting_date != due_date else 0,
                        "service_start_date": posting_date,
                        "service_end_date": due_date,
                        # Item tax template will be automatically applied from item master
                        "item_tax_template": get_item_tax_template(item_doc)
                    })

                    # Calculate taxes based on item tax templates
                    invoice.run_method("calculate_taxes_and_totals")
                    
                    invoice.save(ignore_permissions=True)
                    invoice.submit()
                    service.invoice_number = invoice.name
                    service.db_update()


def apply_taxes_template(invoice, lease_doc, company_doc):
    """
    Apply appropriate taxes template to the invoice
    Checks in order: Lease Contract setting → Customer setting → Company default
    """
    taxes_template = None
    
    # 1. Check if there's a taxes template in the Lease Contract (custom field)
    if hasattr(lease_doc, 'taxes_and_charges'):
        taxes_template = lease_doc.taxes_and_charges
    
    # 2. If not, check customer's default taxes template
    if not taxes_template:
        customer_doc = frappe.get_doc("Customer", lease_doc.tenant_lessee)
        if hasattr(customer_doc, 'default_sales_taxes_and_charges_template'):
            taxes_template = customer_doc.default_sales_taxes_and_charges_template
    
    # 3. If not, use company's default
    if not taxes_template and hasattr(company_doc, 'default_sales_taxes_and_charges_template'):
        taxes_template = company_doc.default_sales_taxes_and_charges_template
    
    # Apply the template if found
    if taxes_template:
        invoice.taxes_and_charges = taxes_template
        # Load the tax template details into the invoice
        tax_template = frappe.get_doc("Sales Taxes and Charges Template", taxes_template)
        for tax in tax_template.taxes:
            invoice.append("taxes", {
                "charge_type": tax.charge_type,
                "account_head": tax.account_head,
                "description": tax.description,
                "rate": tax.rate,
                "cost_center": tax.cost_center or company_doc.cost_center,
                "included_in_print_rate": tax.included_in_print_rate
            })


def get_item_tax_template(item_doc):
    """
    Get the item tax template from the item master if it exists
    """
    if hasattr(item_doc, 'item_tax_template') and item_doc.item_tax_template:
        return item_doc.item_tax_template
    
    # If no direct template, check the taxes table in item
    if hasattr(item_doc, 'taxes') and item_doc.taxes:
        # Item has custom tax rates defined
        # These will be automatically applied by ERPNext
        return None
    
    return None


def create_individual_invoice(lease_doc, payment_row, schedule_doc):
    try:
        company_doc = frappe.get_doc("Company", lease_doc.owner_lessor)
        if not lease_doc.tenant_lessee:
            frappe.throw(f"Lease Contract {lease_doc.name} has no Tenant/Customer linked!")
            return

        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer = lease_doc.tenant_lessee

        posting_date = payment_row.lease_start
        due_date = payment_row.lease_end
        invoice.set_posting_time = 1
        invoice.posting_date = str(posting_date)
        invoice.due_date = str(due_date)
        invoice.custom_lease_contract = lease_doc.name
        invoice.debit_to = company_doc.default_receivable_account if company_doc.default_receivable_account else frappe.throw(f"Please set Default Receivable Account in Company Settings")

        # Apply taxes template BEFORE adding items
        apply_taxes_template(invoice, lease_doc, company_doc)

        item_codes = frappe.get_all("Lease Contract Details",
            filters={
                "parent": lease_doc.name,
            },
            fields=["rent_item", "amount"]
        )                
         
        if not item_codes:
            frappe.throw(f"No items found in Lease Contract {lease_doc.name} to create invoice.")

        total_months = rounded(flt(getattr(lease_doc, 'period_in_months', 0)) / flt(getattr(lease_doc, 'billing_frequency', 1)), 6)
        if not lease_doc.contract_multi_period:
            if lease_doc.allowance_period and lease_doc.in_period:
                total_months = rounded(total_months - flt(lease_doc.allowance_period), 6)
        
        for item in item_codes:
            item_doc = frappe.get_doc("Item", item.rent_item)
            if not lease_doc.contract_multi_period:
                item_rate = rounded(flt(item.amount) / total_months, 6)
                
                invoice.append("items", {
                    "item_code": item.rent_item,
                    "item_name": item_doc.item_name,
                    "item_group": item_doc.item_group,
                    "qty": 1,
                    "rate": item_rate,
                    "uom": item_doc.stock_uom,
                    "income_account": company_doc.default_income_account if company_doc.default_income_account else frappe.throw(f"Please set Default Income Account in Company Settings"),
                    "enable_deferred_revenue": 1,
                    "service_start_date": posting_date,
                    "service_end_date": due_date,
                    # Item tax template will be automatically applied from item master
                    "item_tax_template": get_item_tax_template(item_doc)
                })
        
        # Calculate taxes based on item tax templates
        invoice.run_method("calculate_taxes_and_totals")

        invoice.save(ignore_permissions=True)
        invoice.submit()

        frappe.msgprint(f"Sales Invoice {invoice.name} created for period {payment_row.lease_start} to {payment_row.lease_end}", alert=True, indicator="green")

        payment_row.invoice_number = invoice.name
        payment_row.invoice_status = invoice.status
        schedule_doc.save(ignore_permissions=True)

    except Exception as e:
        frappe.throw(f"Failed to create invoice for payment period: {str(e)}")

        
def create_multi_period_invoices(lease_doc, payment_row, schedule_doc):
    try:
        company_doc = frappe.get_doc("Company", lease_doc.owner_lessor)
        if not lease_doc.tenant_lessee:
            frappe.throw(f"Lease Contract {lease_doc.name} has no Tenant/Customer linked!")

        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer = lease_doc.tenant_lessee

        posting_date = payment_row.lease_start
        due_date = payment_row.lease_end
        invoice.set_posting_time = 1
        invoice.posting_date = str(posting_date)
        invoice.due_date = str(due_date)
        invoice.custom_lease_contract = lease_doc.name
        invoice.debit_to = company_doc.default_receivable_account or frappe.throw("Please set Default Receivable Account in Company Settings")

        # Apply taxes template BEFORE adding items
        apply_taxes_template(invoice, lease_doc, company_doc)

        period = None
        for p in lease_doc.period_details:
            if getdate(p.from_date) <= getdate(posting_date) <= getdate(p.to_date):
                period = p
                break

        if not period:
            frappe.throw(f"No matching period detail found for posting date {posting_date} in Lease {lease_doc.name}")

        period_months = flt(period.month_in_period)
        if period_months <= 0:
            frappe.throw("Invalid 'month_in_period' value in period details.")

        if lease_doc.allowance_period and lease_doc.in_period and period == lease_doc.period_details[0]:
            period_months = rounded(period_months - flt(lease_doc.allowance_period), 6)

        service_rent_monthly = rounded(flt(period.service_amount) / period_months, 6)
        space_rent_monthly = rounded(flt(period.space_amount) / period_months, 6)
        
        for rent_item in lease_doc.rent_details:
            item_doc = frappe.get_doc("Item", rent_item.rent_item)
            monthly_rate = space_rent_monthly if rent_item.is_stock_item else service_rent_monthly
            invoice_rate = rounded(monthly_rate * flt(lease_doc.billing_frequency), 6)

            invoice.append("items", {
                "item_code": rent_item.rent_item,
                "item_name": item_doc.item_name,
                "item_group": item_doc.item_group,
                "qty": 1,
                "rate": invoice_rate,
                "uom": item_doc.stock_uom,
                "income_account": company_doc.default_income_account or frappe.throw("Please set Default Income Account in Company Settings"),
                "enable_deferred_revenue": 1,
                "service_start_date": posting_date,
                "service_end_date": due_date,
                # Item tax template will be automatically applied from item master
                "item_tax_template": get_item_tax_template(item_doc)
            })

        # Calculate taxes based on item tax templates
        invoice.run_method("calculate_taxes_and_totals")

        invoice.save(ignore_permissions=True)
        invoice.submit()

        payment_row.invoice_number = invoice.name
        payment_row.invoice_status = invoice.status
        schedule_doc.save(ignore_permissions=True)

    except Exception as e:
        frappe.throw(f"Failed to create multi-period invoice: {str(e)}")


def get_tax_breakdown_summary(invoice_name):
    """
    Utility function to get tax breakdown summary for an invoice
    Can be used for reporting or verification
    """
    invoice = frappe.get_doc("Sales Invoice", invoice_name)
    
    tax_summary = {}
    
    for item in invoice.items:
        if item.item_tax_rate:
            import json
            try:
                item_taxes = json.loads(item.item_tax_rate)
                
                for tax_account, tax_rate in item_taxes.items():
                    key = f"{tax_account} @ {tax_rate}%"
                    
                    if key not in tax_summary:
                        tax_summary[key] = {
                            "tax_account": tax_account,
                            "rate": tax_rate,
                            "taxable_amount": 0,
                            "tax_amount": 0,
                            "items": []
                        }
                    
                    tax_amount = flt(item.amount * flt(tax_rate) / 100, 2)
                    tax_summary[key]["taxable_amount"] += item.amount
                    tax_summary[key]["tax_amount"] += tax_amount
                    tax_summary[key]["items"].append({
                        "item_code": item.item_code,
                        "amount": item.amount,
                        "tax_amount": tax_amount
                    })
            except:
                pass
    
    return tax_summary


def validate_tax_configuration():
    """
    Validation function to check if tax configuration is proper
    Can be run as a scheduled job or manually
    """
    issues = []
    
    # Check if items have tax templates or tax configurations
    items = frappe.get_all("Item", 
        filters={"disabled": 0, "is_sales_item": 1},
        fields=["name", "item_name"]
    )
    
    for item in items:
        item_doc = frappe.get_doc("Item", item.name)
        
        # Check if item has tax configuration
        has_tax_template = hasattr(item_doc, 'item_tax_template') and item_doc.item_tax_template
        has_tax_table = hasattr(item_doc, 'taxes') and len(item_doc.taxes) > 0
        
        if not has_tax_template and not has_tax_table:
            issues.append({
                "item": item.name,
                "item_name": item.item_name,
                "issue": "No tax configuration found"
            })
    
    return issues