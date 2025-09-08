// Copyright (c) 2025, KCSC and contributors
// For license information, please see license.txt

// All business logic for tenant, rent_space, and disabling Floor Unit
// is now handled in the backend (Python).
// The following code is commented out and not needed.

// frappe.ui.form.on("Floor Unit", {
//     tenant: function(frm) {
//         update_floor_unit(frm, frm.doc.tenant, 1);
//     },

//     rent_space: function(frm) {
//         if (frm.doc.rent_space === 0) {
//             update_floor_unit(frm, "", 0);
//         }
//     },

//     // disable: function(frm) {
//     //     if (frm.doc.disable === 1) {
//     //         disable_floor_unit(frm);
//     //     }
//     // }
// });

// /**
//  * Update tenant and rent_space on linked Stock Entry
//  */
// function update_floor_unit(frm, tenant, rent_space_value) {
//     if (!frm.doc.ref_doc) return;

//     frappe.call({
//         method: "masar_mall.masar_mall.doctype.floor_unit.floor_unit.st_update",
//         args: {
//             name: frm.doc.ref_doc,
//             tenant: tenant
//         },
//         callback: function() {
//             frm.set_value('tenant', tenant);
//             frm.set_value('rent_space', rent_space_value);

//             frm.save_or_update()
//                 .then(() => frappe.show_alert("Tenant and Rent Space successfully updated."))
//                 .catch(err => {
//                     frappe.show_alert(`Error updating Floor Unit: ${err.message}`);
//                     console.error(err);
//                 });
//         }
//     });
// }

// /**
//  * Disable Floor Unit by creating and submitting a Stock Entry
//  */
// function disable_floor_unit(frm) {
//     if (!frm.doc.ref_doc) return;

//     frappe.call({
//         method: "masar_mall.masar_mall.doctype.floor_unit.floor_unit.st_disable_floor_unit",
//         args: { floor_unit_name: frm.doc.name }, // pass the name string
//         callback: function(r) {
//             frm.set_value('disable', 1);

//             frm.save_or_update()
//                 .then(() => frappe.show_alert("Floor Unit successfully disabled."))
//                 .catch(err => {
//                     frappe.show_alert(`Error disabling Floor Unit: ${err.message}`);
//                     console.error(err);
//                 });
//         }
//     });
// }

// Only keep setup logic for floor query
frappe.ui.form.on("Floor Unit", {
    setup: function (frm) {
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
    },

    property: function (frm) {
        frm.refresh_field("floor");
    }
});
