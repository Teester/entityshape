entitycheck_stylesheet = entitycheck_getStylesheet();
$('html > head').append("<style>" + entitycheck_stylesheet + "</style>");

$(document).ready(function(){
	var entityID = mw.config.get( 'wbEntityId' );
	var lang = mw.config.get( 'wgUserLanguage' );
	if (entityID) {
        var schema = window.localStorage.getItem("entitycheck");
        var value = window.localStorage.getItem("entitycheck-auto");
        var entitycheck_entityTitle = document.location.pathname.substring(6)
        if (value == "true") {
            entitycheck_checkEntity(entitycheck_entityTitle, schema, lang);
            $("#entitycheck-checkbox").prop('checked', true)
        } else {
            $("#entitycheck-checkbox").prop('checked', false)
        }
        $("#entityschema-entityToCheck:text").val(schema);
    }
});

var entitycheck_conditions = ["/wiki/Q", "/wiki/P", "/wiki/L"];
if (entitycheck_conditions.some(el => document.location.pathname.includes(el))) {
	var entitycheck_entity_html = '<div><span id="entityschema-simpleSearch"><span>'
	entitycheck_entity_html += '<input type="text" id="entityschema-entityToCheck" placeholder="Enter a schema to check against e.g. E234">'
	entitycheck_entity_html += '<input type="submit" id="entityschema-schemaSearchButton" class="searchButton" onClick="entitycheck_update()" name="check" value="Check">'
	entitycheck_entity_html += '</span></span><input type="checkbox" id="entitycheck-checkbox" onclick="entitycheck_checkbox()">'
	entitycheck_entity_html += '<label for="entitycheck-checkbox"><small>Automatically check schema</small></label><span id="entityCheckResponse"></span></div>';
	var entitycheck_entityTitle = $(".wikibase-title-id" )[0].innerText;
	if (document.location.pathname.includes("/wiki/L")) {
		$(".mw-indicators" ).append( entitycheck_entity_html );
	} else {
		$(".wikibase-entitytermsview-heading" ).append( entitycheck_entity_html );
	}
}

$("#entityschema-entityToCheck").on("keyup", function(event){
    console.log(event)
    if (event.key === "Enter") {
        event.preventDefault();
        $("#entityschema-schemaSearchButton").click()
        return false;
    }
});

function entitycheck_update() {
    var entitycheck_entitySchema = $("#entityschema-entityToCheck")[0].value.toUpperCase();
    var entitycheck_entityTitle = document.location.pathname.substring(6)
    var lang = mw.config.get( 'wgUserLanguage' );
    window.localStorage.setItem("entitycheck", entitycheck_entitySchema);
	entitycheck_checkEntity(entitycheck_entityTitle, entitycheck_entitySchema, lang);
}

function entitycheck_checkbox() {
    if ($('#entitycheck-checkbox').is(":checked")) {
        window.localStorage.setItem("entitycheck-auto", true);
    } else {
        window.localStorage.setItem("entitycheck-auto", false);
    }
}

function entitycheck_checkEntity(entity, entitySchema, language) {
	$("#entityCheckResponse").contents().remove();
    $(".entitycheck-property").remove()
	// var url = "https://tools.wmflabs.org/entitycheck/api?entityschema=" + entitySchema + "&entity=" + entity + "&language=" + language;
	var url = "http://127.0.0.1:5000/api?entityschema=" + entitySchema + "&entity=" + entity + "&language=" + language;
	console.log(url)
	$.ajax({ 
		type: "GET",
		dataType: "json",
		url: url,
		success: function(data){
		console.log(data);
			var html = "";
			var response = "missing";
			properties = $(".wikibase-statementgroupview")
			var not_in_required = []
            var property_list = []
            var missing_properties = []
            for (var property = 0; property < properties.length; property++) {
                property_list.push(properties[property]["id"])
            }
			html += "<br/>Checking against <b><a href='https://www.wikidata.org/wiki/EntitySchema:" + data.schema + "'>" + data.schema + ":" + data.name + '</a></b>:';
			if (data.validity.results) {
                if (data.validity.results[0].result) {
                    html += '<span class="response"><span class="pass">✔</span><span> Pass</span></span><br/>';
                } else {
                    html += entitycheck_parseResult(data.validity.results[0]);
                }
            }
			html += '<div style="overflow-y: scroll; max-height:200px;"><table style="width:100%;"><th class="entitycheck_table">Required properties</th>';
			html += '<th class="entitycheck_table">Optional properties</th>';
			html += '<th class="entitycheck_table">Properties not in schema</th><tr>';

            var required_html = '<td class="entitycheck_table">'
            var optional_html = '<td class="entitycheck_table">'
            var absent_html = '<td class="entitycheck_table">'
            if (data.properties) {
                for (var key in data.properties) {
                    shape_html = ""
                    var response = data.properties[key]["response"]
                    var response_class  = ""
                    switch (response) {
                        case "present":
                            response_class = "present"
                            break;
                        case "correct":
                            response_class = "correct"
                            break;
                        case "missing":
                            response_class = "missing"
                            break;
                        default:
                            response_class = "wrong"
                            break;
                    }
                    if (response == null) {
                        response = "";
                        shape_html += '<a href="https://www.wikidata.org/wiki/Property:' + key;
                        shape_html +='">'+ key + " - <small>" + data.properties[key]["name"] + '</small></a><br/>';
                    } else {
                        shape_html += '<span class=entitycheck-' + response_class + '>' + response + '</span><a href="https://www.wikidata.org/wiki/Property:' + key;
                        shape_html +='" class="is_entitycheck-'+ response_class+'">'+ key + " - <small>" + data.properties[key]["name"] + '</small></a><br/>';
                    }
                    switch (data.properties[key]["necessity"]){
                        case "required":
                            required_html += shape_html;
                            break;
                        case "optional":
                            optional_html += shape_html;
                            break;
                        default:
                            absent_html += shape_html;
                            break
                    }
                    if (!response) {
                        response = "Not in schema"
                        response_class = "missing"
                    }
                    if ($("#" + key)[0]) {
                        $("#" + key + " .wikibase-statementgroupview-property-label").append("<br class='entitycheck-property'/><div style='display:inline-block;' class='entitycheck-property entitycheck-" + response_class + "' title='" + data.schema + ": " + data.name + "'>" + data.schema + ": " + response + "</div>");
                    }
                }
            }
            required_html += "</td>"
            optional_html += "</td>"
            absent_html += "</td>"
            html += required_html + optional_html + absent_html
			html += '</tr></table></div>'

			$("#entityCheckResponse" ).append( html );

			if (data.statements) {
			    for (var statement in data.statements) {
			        var response = data.statements[statement].response
                    if (response != "not in schema") {
    			        html = "<br class='entitycheck-property'/><span class='entitycheck-property entitycheck-" + response + "'>" + response + "</span>"
	    		        $("div[id='" + statement + "'] .wikibase-toolbar-button-edit").append(html)
			        }
			    }
			}
		},
		error: function(data) {
			$("#entityCheckResponse").append( '<span>Unable to validate schema</span>' );
		}
	});
}

function entitycheck_parseResult(data) {
	var property = [];
	var html = '<span class="response" title="' + data.reason + '"><span class="fail">✘</span><span class="response"> Fail</span>';
	var no_matching_triples = "No matching triples found for predicate";
	if (data.reason.includes(no_matching_triples)) {
		property = data.reason.match(/P\d+/g);
	}
	if (property !== null) {
		property = property.reduce(function(a,b){if(a.indexOf(b)<0)a.push(b);return a;},[]);
		for (var i = 0; i < property.length; i++) {
			html += '<span class="missing"> Missing valid ' + property[i] + '</span>';
		}
	}
	html += "</span>";
	return html;
}

function entitycheck_getStylesheet() {
    var stylesheet = "#schemaSearchButton { background-position: center center; background-repeat: no-repeat; position: absolute; top:0; right:0; overflow: hidden; height:100%; background-color: #1E90FF !important; color: #FFFFFF !important; padding: 2px !important}";
    stylesheet += "#entityToCheck { padding: 1em; margin:0; width: 100%;}";
    stylesheet += ".response { padding: 2px;}";
    stylesheet += "a.is_entitycheck-present { color: #008800; }";
    stylesheet += "a.is_entitycheck-allowed { color: #008800; }";
    stylesheet += "a.is_entitycheck-correct { color: #00CC00; }";
    stylesheet += "a.is_entitycheck-missing { color: #FF8C00; }";
    stylesheet += "a.is_entitycheck-wrong { color: #CC0000; }";
    stylesheet += "a.is_entitycheck-wrong_amount { color: #CC0000; }";
    stylesheet += "a.is_entitycheck-incorrect { color: #CC0000; }";
    stylesheet += ".entitycheck_table {vertical-align: top; width: 33%;} "
    stylesheet += ".entitycheck-missing { background-color: #FF8C00; color: #ffffff; padding:2px; margin: 2px; font-size:75%; border-radius:2px;}";
    stylesheet += ".entitycheck-wrong { background-color: #CC0000; color: #ffffff; padding:2px; margin: 2px; font-size:75%; border-radius:2px;}";
    stylesheet += ".entitycheck-incorrect { background-color: #CC0000; color: #ffffff; padding:2px; margin: 2px; font-size:75%; border-radius:2px;}";
    stylesheet += ".entitycheck-wrong_amount { background-color: #CC0000; color: #ffffff; padding:2px; margin: 2px; font-size:75%; border-radius:2px;}";
    stylesheet += ".entitycheck-excess { background-color: #CC0000; color: #ffffff; padding:2px; margin: 2px; font-size:75%; border-radius:2px;}";
    stylesheet += ".entitycheck-deficit { background-color: #CC0000; color: #ffffff; padding:2px; margin: 2px; font-size:75%; border-radius:2px;}";
    stylesheet += ".entitycheck-present { background-color: #008800; color: #ffffff; padding:2px; margin: 2px; font-size:75%; border-radius:2px;}";
    stylesheet += ".entitycheck-allowed { background-color: #008800; color: #ffffff; padding:2px; margin: 2px; font-size:75%; border-radius:2px;}";
    stylesheet += ".entitycheck-correct { background-color: #00CC00; color: #ffffff; padding:2px; margin: 2px; font-size:75%; border-radius:2px;}";
    return stylesheet;
}
