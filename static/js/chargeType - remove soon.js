// periods in ids cause problems, this function fixes it https://learn.jquery.com/using-jquery-core/faq/how-do-i-select-an-element-by-an-id-that-has-characters-used-in-css-notation/
function jq(myid) {
    return "#" + myid.replace(/(:|\.|\[|\]|,|=|@)/g, "\\$1");
}

$(function () {
    $('select[name="chargeType"]').change(function () {
        $.ajax({
            url: '/import_transactions/stage/charge_type',
            // "this" was important
            data: $(this.form).serialize(),
            type: 'POST',
            success: function (response) {
                console.log(response);
                // the next line finds the id of the corresponding charge type and sets its value to what was defined in the response
                $(jq(response.ccformid)).val(response.ccdef);
                //same for tracking type
                $(jq(response.ttformid)).val(response.ttdef);
            },
            error: function (error) {
                console.log(error);
            }
        });
    });
});