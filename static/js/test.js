$(function(){
    $.getJSON("mps.json", function(mps) {
        $("#output").pivotUI(mps, {
            rows: ["Province"],
            cols: ["Party"],
            aggregatorName: "Integer Sum",
            vals: ["Age"],
            rendererName: "Heatmap",
            rendererOptions: {
                table: {
                    clickCallback: function(e, value, filters, pivotData){
                        var names = [];
                        pivotData.forEachMatchingRecord(filters,
                            function(record){ names.push(record.Name); });
                        alert(names.join("\n"));
                    }
                }
            }
        });
    });
 });

 $(function(){
    if(window.location != window.parent.location)
        $("<a>", {target:"_blank", href:""})
            .text("[pop out]").prependTo($("body"));

    $("#output").pivotUI(
        $.csv.toArrays($("#output").text()),
        $.extend({
            renderers: $.extend(
                $.pivotUtilities.renderers,
                $.pivotUtilities.c3_renderers,
                $.pivotUtilities.d3_renderers,
                $.pivotUtilities.export_renderers
                ),
            hiddenAttributes: [""],     
            rendererOptions: {
                table: {
                    clickCallback: function(e, value, filters, pivotData){
                        var names = [];
                        pivotData.forEachMatchingRecord(filters,
                            function(record){ names.push(record.transaction_id); });
                        alert(names.join("\n"));
                    }
                }
            }            
            
        },         
        %(kwargs)s)
    ).show();
});


$(function(){
    if(window.location != window.parent.location)
        $("<a>", {target:"_blank", href:""})
            .text("[pop out]").prependTo($("body"));

    $("#output").pivotUI(
        $.csv.toArrays($("#output").text()),
        $.extend({
            renderers: $.extend(
                $.pivotUtilities.renderers,
                $.pivotUtilities.c3_renderers,
                $.pivotUtilities.d3_renderers,
                $.pivotUtilities.export_renderers
                ),
            hiddenAttributes: [""],     
            rendererOptions: {
                table: {
                    clickCallback: function(e, value, filters, pivotData){
                        var names = [];
                        pivotData.forEachMatchingRecord(filters,
                            function(record){ names.push(record.Name); });
                        alert(names.join("
"));
                    }
                }
            }            
            
        },         
        {"rows": ["Transaction Month"]})
    ).show();
});