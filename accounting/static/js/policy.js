(function () {
    'use strict';
    requirejs.config({
        //baseUrl: "",
        urlArgs: "bust=8" ,
        paths: {
            'knockout': '//cdnjs.cloudflare.com/ajax/libs/knockout/3.3.0/knockout-min',
            'knockout.validation': '//cdnjs.cloudflare.com/ajax/libs/knockout-validation/1.0.2/knockout.validation'
        }
    });

    require(['knockout', 'knockout.validation'], function (ko, domReady) {

        $(function () {

            ko.validation.configure({
                insertMessages: false,
                decorateElement: true,
                errorElementClass: 'error',
                messagesOnModified: false
            });

            ko.extenders.deferValidation = function (target, option) {
                if (option) {
                    target.subscribe(function(){
                        target.isModified(false);
                    });
                }

                return target;
            };

            function PolicyViewModel() {

                var self = this;
                self.policyId = ko.observable().extend({
                    required: {message: 'Policy id is required' },
                    deferValidation: true
                });

                self.date_ = ko.observable().extend({
                    required: {message: "Date is required" },
                    deferValidation: true
                });


                self.errors = ko.validation.group(self);
                self.click = function (e) {
                    if (self.errors().length > 0) {
                        self.errors.showAllMessages(true);
                        this.errors().forEach(function(data) {
                        alert(data);
                       });
                    } else {
                      $("#form-policy").submit();
                    }
                };

            }
            $(function () {
                ko.applyBindings(new PolicyViewModel());
            });

        });

    });


})();


// ko.validation.configure({
//     insertMessages: false,
//     decorateElement: true,
//     errorElementClass: 'error',
//     messagesOnModified: false
// });
//
// ko.extenders.deferValidation = function (target, option) {
//     if (option) {
//         target.subscribe(function(){
//             target.isModified(false);
//         });
//     }
//
//     return target;
// };
//
// function PolicyViewModel() {
//
//     var self = this;
//     self.policyId = ko.observable().extend({
//         required: {message: 'Policy id is required' },
//         deferValidation: true
//     });
//
//     self.date_ = ko.observable().extend({
//         required: {message: "Date is required" },
//         deferValidation: true
//     });
//
//
//     self.errors = ko.validation.group(self);
//     self.submit = function (e) {
//         if (self.errors().length > 0) {
//             self.errors.showAllMessages(true);
//             this.errors().forEach(function(data) {
//             alert(data);
//            });
//         }
//     };
//
// }
// $(function () {
//     ko.applyBindings(new PolicyViewModel());
// });
