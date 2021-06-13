// periods in ids cause problems, this function fixes it https://learn.jquery.com/using-jquery-core/faq/how-do-i-select-an-element-by-an-id-that-has-characters-used-in-css-notation/
function jq(myid) {
    return "#" + myid.replace(/(:|\.|\[|\]|,|=|@)/g, "\\$1");
}

$(function () {
    $('select[name="bankCol"]').change(function () {
        $.ajax({
            url: '/bankTemplates/modCol',
            // "this" was important
            data: $(this.form).serialize(),
            type: 'POST',
            success: function (response) {
                console.log(response);
                // I don't think I needed any of the stuff here
            },
            error: function (error) {
                console.log(error);
            }
        });
    });
});