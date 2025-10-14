// Copyright (c) 2025, KCSC and contributors
// For license information, please see license.txt

frappe.ui.form.on('Lease Contract', {
    refresh: function (frm) {
        filter_tax(frm);
        create_custom_buttons(frm);
        filter_rent_details(frm);
        calculate_totals(frm);
       frm.set_df_property("rent_schedule", "options", generate_rent_schedule_html(frm));
       frm.refresh_field("rent_schedule");
        
    },

    validate: function (frm) {
        calculate_totals(frm);
            
            frm.set_df_property("rent_schedule", "options", generate_rent_schedule_html(frm));
            frm.refresh_field("rent_schedule");
        
    },

    rent_details: function (frm, cdt, cdn) {
        calculate_totals(frm);
    },

    setup: function (frm) {
        filter_tax(frm);
        filter_floor(frm);
    },

    onload: function (frm) {
        filter_tax(frm);
        filter_rent_details(frm);
    },

    property: function (frm) {
        filter_rent_details(frm);
        frm.refresh_field("floor");
    },

    owner_lessor: function (frm) {
        filter_tax(frm);
    }
});

frappe.ui.form.on('Lease Contract Details', {
    rate: function (frm, cdt, cdn) {
        calculate_row_amount(frm, cdt, cdn);
        recalculate_service_items(frm);
    },

    amount: function (frm, cdt, cdn) {
        calculate_row_amount(frm, cdt, cdn);
        recalculate_service_items(frm);
    },

    rent_item: function (frm, cdt, cdn) {
        calculate_row_amount(frm, cdt, cdn);
        recalculate_service_items(frm);
        calculate_totals(frm);
    },

    rent_details_remove: function (frm) {
        calculate_totals(frm);
    }
});

function calculate_row_amount(frm, cdt, cdn) {
    const child = locals[cdt][cdn];
    if (!child.rent_item) return;

    const is_stock_item = child.is_stock_item;
    const service_percentage = flt(child.custom_service_percentage);
    let amount = 0;

    if (is_stock_item) {
        amount = flt(child.rate);
    } else {
        if (service_percentage > 0) {
            const total_stock_amount = get_total_stock_amount(frm);
            amount = (service_percentage / 100) * total_stock_amount;
        } else {
            amount = flt(child.rate);
        }
    }

    frappe.model.set_value(cdt, cdn, "rate", amount);
    frappe.model.set_value(cdt, cdn, "amount", amount);
}

function get_total_stock_amount(frm) {
    let total = 0;
    (frm.doc.rent_details || []).forEach(row => {
        if (row.is_stock_item) {
            total += flt(row.amount);
        }
    });
    return total;
}

function recalculate_service_items(frm) {
    const total_stock_amount = get_total_stock_amount(frm);

    (frm.doc.rent_details || []).forEach(row => {
        if (!row.is_stock_item && flt(row.custom_service_percentage) > 0) {
            const new_amount = (flt(row.custom_service_percentage) / 100) * total_stock_amount;
            frappe.model.set_value(row.doctype, row.name, "rate", new_amount);
            frappe.model.set_value(row.doctype, row.name, "amount", new_amount);
        }
    });
}

function get_total_stock_amount(frm) {
    let total = 0;
    (frm.doc.rent_details || []).forEach(row => {
        if (row.is_stock_item) {
            total += flt(row.amount);
        }
    });
    return total;
}

function recalculate_service_items(frm) {
    (frm.doc.rent_details || []).forEach(row => {
        if (row.rent_item && !row.is_stock_item) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Item",
                    filters: { name: row.rent_item },
                    fieldname: ["custom_service_percentage"]
                },
                callback: function(r) {
                    if (!r.message) return;
                    let percentage = flt(r.message.custom_service_percentage);
                    if (percentage > 0) {
                        let total_stock = get_total_stock_amount(frm);
                        let new_amount = (percentage / 100) * total_stock;
                        frappe.model.set_value(row.doctype, row.name, "rate", new_amount);
                        frappe.model.set_value(row.doctype, row.name, "amount", new_amount);
                    }
                }
            });
        }
    });
}


function calculate_totals(frm) {
    let total_elements = 0;
    let total_amount = 0;

    if (frm.doc.rent_details) {
        frm.doc.rent_details.forEach(row => {
            if (row.amount !== undefined) {
                total_elements++;
                total_amount += flt(row.amount);
            }
        });
    }

    frm.set_value("total_rent_elements", total_elements);
    frm.set_value("total_rent_amount", total_amount);

    frm.refresh_field("total_rent_elements");
    frm.refresh_field("total_rent_amount");
}

function filter_rent_details(frm) {
    const grid = frm.fields_dict.rent_details.grid;
    const floor_unit_field = grid.get_field("floor_unit");

    if (!floor_unit_field.hasOwnProperty('original_get_query')) {
        floor_unit_field.original_get_query = floor_unit_field.get_query;
    }

    floor_unit_field.get_query = function () {
        if (frm.doc.docstatus === 0 && frm.doc.property) {
            return {
                filters: {
                    property: frm.doc.property,
                    docstatus: 1,
                    disabled: 0,
                    floor: frm.doc.floor || null
                }
            };
        }
        return { filters: { name: "" } };
    };
}

function filter_floor(frm) {
    frm.set_query("floor", function () {
        if (!frm.doc.property) {
            frappe.msgprint(__('Please select a Property first.'));
            return { filters: { name: "" } };
        }

        return {
            filters: {
                property: frm.doc.property,
                disable: 0,
                docstatus: 1
            }
        };
    });
}

function filter_tax(frm) {
    frm.set_query("tax_template", function () {
        if (!frm.doc.owner_lessor) {
            frappe.msgprint(__('Please select a Company first.'));
            return { filters: { name: "" } };
        }

        return {
            filters: {
                company: frm.doc.owner_lessor,
            }
        };
    });
}

function create_custom_buttons(frm) {
    if (frm.doc.docstatus === 1 && frm.doc.status === "Rent") {

        frm.add_custom_button(__('Renewal'), function () {
            let renewed_from = frm.doc.name;

            setTimeout(function () {
                frappe.new_doc("Lease Contract", {
                    renewed_from: renewed_from,
                    tenant_lessee: frm.doc.tenant_lessee,
                    property: frm.doc.property,
                    floor: frm.doc.floor,
                    represented_by: frm.doc.represented_by,
                    rent_details: frm.doc.rent_details,
                    lease_start: frm.doc.lease_end,
                    lease_end: null,
                    billing_frequency: frm.doc.billing_frequency,
                    allowance_period: frm.doc.allowance_period,
                    in_periodic: frm.doc.in_periodic,
                    out_periodic: frm.doc.out_periodic,
                    accommodation_type: frm.doc.accommodation_type,
                });
            }, 500);
        }, __("Manage"));

        frm.add_custom_button(__('Terminate'), function () {
            frappe.confirm(
                __('<b>Are you sure you want to terminate this lease contract? This action cannot be undone.</b>'),
                function () {
                    frappe.call({
                        doc: frm.doc,
                        method: "terminate_lease",
                        callback: function (r) {
                            if (!r.exc) frm.reload_doc();
                        }
                    });
                }
            );
        }, __("Manage"));

        frm.add_custom_button(__('Legal Case'), function () {
            frappe.confirm(
                __('<b>Are you sure you want to put a legal case for this lease contract?</b>'),
                function () {
                    frappe.call({
                        doc: frm.doc,
                        method: "legal_case",
                        callback: function (r) {
                            if (!r.exc) frm.reload_doc();
                        }
                    });
                }
            );
        }, __("Manage"));
    }
}

/**
 * Generates and displays an HTML rent schedule table for a Lease Contract
 * This function fetches invoice data from the Lease Contract Schedule and renders
 * it as a formatted table showing payment periods and cumulative totals
 * 
 * @param {object} frm - The Frappe form object containing the current Lease Contract
 */
function generate_rent_schedule_html(frm) {
    // Display a loading indicator to inform users that data is being fetched
    // This provides immediate feedback while API calls are in progress
    frm.fields_dict['rent_schedule'].html("<p>Loading rent schedule...</p>");

    // VALIDATION: Ensure the lease contract document has been saved to the database
    // Without a saved document, there's no name/ID to query against
    if (!frm.doc.name) {
        frm.fields_dict['rent_schedule'].html(
            "<p style='color:red;'>Lease Contract must be saved before loading schedule.</p>"
        );
        return; // Exit early to prevent unnecessary API calls
    }

    // STEP 1: Query the database to find the Lease Contract Schedule linked to this contract
    // We only want submitted schedules (docstatus: 1) to ensure data integrity
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Lease Contract Schedule",
            filters: { 
                lease_contract: frm.doc.name,  // Match schedules linked to this contract
                docstatus: 1                    // Only include submitted/finalized schedules (not drafts or cancelled)
            },
            fields: ["name"],                   // We only need the schedule name/ID for now
            limit_page_length: 1                // Limit to one result since each contract should have one schedule
        },
        callback: function (response) {
            // Handle case where no schedule exists for this contract
            // This might happen if the schedule hasn't been created yet
            if (!response.message || response.message.length === 0) {
                frm.fields_dict['rent_schedule'].html(
                    "<p style='color:orange;'>No Lease Contract Schedule found for this contract.</p>"
                );
                return; // Exit early since there's no data to display
            }

            // Extract the schedule name from the query results
            const scheduleName = response.message[0].name;

            // STEP 2: Fetch the complete schedule document including its invoice child table
            // This retrieves all the payment/invoice rows associated with the schedule
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Lease Contract Schedule",
                    name: scheduleName
                },
                callback: function (scheduleResponse) {
                    // Extract the schedule document and its invoice child table
                    const leaseSchedule = scheduleResponse.message || {};
                    let invoiceList = leaseSchedule.invoice || [];

                    // SORTING: Arrange invoices in chronological order by lease start date
                    // This ensures the table displays periods in the correct sequence
                    // We use slice() to create a copy before sorting to avoid mutating the original array
                    invoiceList = invoiceList.slice().sort(function(invoiceA, invoiceB) {
                        // Convert lease_start to Date objects for comparison
                        // Use epoch (January 1, 1970) as default if date is missing
                        const startDateA = invoiceA.lease_start ? new Date(invoiceA.lease_start) : new Date(0);
                        const startDateB = invoiceB.lease_start ? new Date(invoiceB.lease_start) : new Date(0);
                        
                        // Return negative if A is earlier, positive if B is earlier, 0 if equal
                        return startDateA - startDateB;
                    });

                    // VALIDATION: Check if the schedule contains any invoice rows
                    // An empty schedule can't be displayed as a table
                    if (!invoiceList.length) {
                        frm.fields_dict['rent_schedule'].html(
                            "<p style='color:orange;'>Lease Contract Schedule has no invoice rows.</p>"
                        );
                        return; // Exit since there's no data to render
                    }

                    /**
                     * Formats a date string or Date object into YYYY-MM-DD format
                     * This ensures consistent date display across different browsers and locales
                     * 
                     * @param {string|Date} dateString - The date to format
                     * @returns {string} Formatted date string in YYYY-MM-DD format, or empty string if invalid
                     */
                    function formatDate(dateString) {
                        if (!dateString) return ""; // Handle null/undefined values
                        
                        const date = new Date(dateString);
                        
                        // If date parsing failed, try to extract first 10 characters as fallback
                        if (isNaN(date)) return String(dateString).slice(0, 10);
                        
                        // Use ISO format and extract date portion (YYYY-MM-DD)
                        return date.toISOString().slice(0, 10);
                    }

                    /**
                     * Formats a numeric amount as currency with thousand separators
                     * Example: 1234.56 becomes "1,234.56"
                     * 
                     * @param {number} amount - The numeric amount to format
                     * @returns {string} Formatted currency string with 2 decimal places and commas
                     */
                    function formatCurrency(amount) {
                        // First fix to 2 decimal places, then use regex to add thousand separators
                        // Regex explanation: \B(?=(\d{3})+(?!\d))
                        //   \B = Match position between two word characters (not at word boundary)
                        //   (?=(\d{3})+(?!\d)) = Look ahead for groups of 3 digits not followed by another digit
                        return amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
                    }

                    /**
                     * Calculates the period end date using a three-tier fallback strategy
                     * This handles various scenarios where end dates might not be explicitly defined
                     * 
                     * Strategy priority:
                     * 1. Use explicit lease_end if available (most reliable)
                     * 2. Calculate as day before next period starts (maintains continuity)
                     * 3. Default to last day of start month (reasonable fallback)
                     * 
                     * @param {number} currentIndex - The index of the current invoice in the array
                     * @returns {string} Formatted end date string in YYYY-MM-DD format
                     */
                    function calculatePeriodEndDate(currentIndex) {
                        const currentInvoice = invoiceList[currentIndex];
                        
                        // STRATEGY 1: Use explicitly defined lease_end date if it exists
                        // This is the most accurate source since it's directly specified in the data
                        if (currentInvoice.lease_end) {
                            return formatDate(currentInvoice.lease_end);
                        }

                        // STRATEGY 2: Calculate end date as one day before the next period starts
                        // This ensures no gaps or overlaps between consecutive periods
                        // Only applicable if there's a next invoice and it has a start date
                        if (currentIndex < invoiceList.length - 1 && invoiceList[currentIndex + 1].lease_start) {
                            const nextPeriodStart = new Date(invoiceList[currentIndex + 1].lease_start);
                            // Subtract one day to get the last day of the current period
                            nextPeriodStart.setDate(nextPeriodStart.getDate() - 1);
                            return formatDate(nextPeriodStart);
                        }

                        // STRATEGY 3: Default to the last day of the start month
                        // This is a reasonable assumption for monthly rent periods
                        // Using month + 1 with day 0 gives us the last day of the current month
                        if (currentInvoice.lease_start) {
                            const startDate = new Date(currentInvoice.lease_start);
                            // Create date for day 0 of next month, which is last day of current month
                            const lastDayOfMonth = new Date(startDate.getFullYear(), startDate.getMonth() + 1, 0);
                            return formatDate(lastDayOfMonth);
                        }

                        // If all strategies fail, return empty string
                        return "";
                    }

                    // TABLE GENERATION: Build the HTML table structure
                    // Initialize cumulative total to track running sum of all payments
                    let cumulativeTotal = 0;
                    
                    // Start building HTML with table header
                    // Using inline styles for better compatibility with Frappe's rendering
                    let htmlTable = `
                        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width:100%;">
                            <tr style="background-color:#f2f2f2; text-align:center;">
                                <th>Row #</th>
                                <th>Period Start</th>
                                <th>Period End</th>
                                <th>Amount</th>
                                <th>Total Accumulated</th>
                            </tr>`;

                    // ITERATE through each invoice and generate a table row
                    // The forEach provides both the invoice object and its index
                    invoiceList.forEach((currentInvoice, rowIndex) => {
                        // Format the period start date for display
                        const periodStartDate = formatDate(currentInvoice.lease_start);
                        
                        // Calculate the period end date using our fallback strategy function
                        const periodEndDate = calculatePeriodEndDate(rowIndex);
                        
                        // Parse the invoice amount as a float (defaults to 0 if missing or invalid)
                        const invoiceAmount = parseFloat(currentInvoice.amount || 0);
                        
                        // Add current amount to running total
                        // This shows total rent paid up to and including this period
                        cumulativeTotal += invoiceAmount;

                        // Append a new row to the table with formatted data
                        // Row number is 1-based (rowIndex + 1) for user-friendly display
                        htmlTable += `
                            <tr style="text-align:center;">
                                <td>${rowIndex + 1}</td>
                                <td>${periodStartDate}</td>
                                <td>${periodEndDate}</td>
                                <td>${formatCurrency(invoiceAmount)}</td>
                                <td>${formatCurrency(cumulativeTotal)}</td>
                            </tr>`;
                    });

                    // Close the table tag to complete the HTML structure
                    htmlTable += "</table>";

                    // RENDER: Display the completed HTML table in the form field
                    // This replaces the loading message with the actual schedule data
                    frm.fields_dict['rent_schedule'].html(htmlTable);
                }
            });
        }
    });
}