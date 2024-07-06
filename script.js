(function() {
let entityschema_stylesheet = entityschema_getStylesheet();
$('html > head').append("<style>" + entityschema_stylesheet + "</style>");
let entityschema_list = [];
let value = window.localStorage.getItem("entityschema-auto");
let schema = window.localStorage.getItem("entityschema");

$(document).ready(function(){
    let property_list = [];
    let item_list = [];
	let entityID = mw.config.get( 'wbEntityId' );

    if (value == "true") {
        $("#entityschema-checkbox").prop('checked', true);
    } else {
        $("#entityschema-checkbox").prop('checked', false);
    }

	if (entityID) {
        let url = "https://www.wikidata.org/w/api.php?action=wbgetentities&props=claims&format=json&ids=" + entityID;
        $.ajax({
            type: "GET",
            dataType: "json",
            url: url,
            success: function(data){
                let claims = data["entities"][entityID]["claims"];
                for (let claim in claims) {
                    property_list.push(claim);
                    let statements = claims[claim];
                    for (let statement in statements) {
                        let mainsnak = statements[statement]["mainsnak"];
                        if (mainsnak["datatype"] == "wikibase-item") {
                            if (!item_list.includes(mainsnak["datavalue"]["value"]["id"])) {
                                item_list.push(mainsnak["datavalue"]["value"]["id"]);
                            }
                        }
                    }
                }
            },
            complete: function() {
                check_entity_for_schemas(item_list)
                check_entity_for_schemas(property_list)
            }
        });
    }
});

function check_entity_for_schemas(entity_list) {
    for (let item in entity_list) {
        let url = "https://www.wikidata.org/w/api.php?action=wbgetclaims&property=P12861&format=json&entity=" + entity_list[item];
        $.ajax({
            type: "GET",
            dataType: "json",
            url: url,
            success: function(data) {
                if (data["claims"].hasOwnProperty("P12861")) {
                    entityschema_list.push(data["claims"]["P12861"][0]["mainsnak"]["datavalue"]["value"]["id"]);
                }
            },
        });
    }
}

$(document).ajaxStop(function () {
  if (value == "true") {
     entityschema_update()
  }
  $("#entityschema-entityToCheck:text").val(schema);
  $(this).unbind('ajaxStop');
});

let entityschema_conditions = ["/wiki/Q", "/wiki/P", "/wiki/L"];
if (entityschema_conditions.some(el => document.location.pathname.includes(el))) {
	let entityschema_entity_html = '<div><span id="entityschema-simpleSearch"><span>';
	entityschema_entity_html += '<input type="text" id="entityschema-entityToCheck" placeholder="Enter schema to check against e.g. E234" title="Enter 1 or more schemas to check against separated by commas e.g. E10, E236 or press Check to auto-determine schemas to check">';
	entityschema_entity_html += '<input type="submit" id="entityschema-schemaSearchButton" class="searchButton" name="check" value="Check">';
	entityschema_entity_html += '<div class="entityshape-spinner" style="display:none"><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div></div>'
	entityschema_entity_html += '</span></span><input type="checkbox" id="entityschema-checkbox">';
	entityschema_entity_html += '<label for="entityschema-checkbox"><small>Automatically check schema</small></label><span id="entityschemaResponse"></span></div>';
	$(entityschema_entity_html).insertAfter("#siteSub");
	$("#entityschema-schemaSearchButton").click(function(){ entityschema_update() });
	$("#entityschema-checkbox").click(function() { entityschema_checkbox() })
}

$("#entityschema-entityToCheck").on("keyup", function(event){
	if (event.key === "Enter") {
		event.preventDefault();
		$("#entityschema-schemaSearchButton").click();
		return false;
	}
});

function entityschema_update() {
	let entityschema_entitySchema = $("#entityschema-entityToCheck")[0].value.toUpperCase();
	if (entityschema_entitySchema.length == 0) {
	    entityschema_entitySchema = entityschema_list.join(", ")
    	window.localStorage.setItem("entityschema", "");
	} else {
    	window.localStorage.setItem("entityschema", entityschema_entitySchema);
    }
	if (entityschema_entitySchema.length == 0) {
	    $("#entityschemaResponse").append( '<span>No schemas entered and could not automatically determine schemas to check</span>' );
	} else {
	    let entityschema_entityName = document.location.pathname.substring(6);
	    let lang = mw.config.get( 'wgUserLanguage' );
	    entityschema_checkEntity(entityschema_entityName, entityschema_entitySchema, lang);
	}
}

function entityschema_checkbox() {
	if ($('#entityschema-checkbox').is(":checked")) {
		window.localStorage.setItem("entityschema-auto", true);
	} else {
		window.localStorage.setItem("entityschema-auto", false);
	}
}

function entityschema_checkEntity(entity, entitySchema, language) {
	$("#entityschemaResponse").contents().remove();
	$(".entityschema-property").remove();
    $(".entityschema-span").remove();

	let url = "https://entityshape.toolforge.org/api/v2?entityschema=" + entitySchema + "&entity=" + entity + "&language=" + language;
	// let url = "http://127.0.0.1:5000/api/v2 ?entityschema=" + entitySchema + "&entity=" + entity + "&language=" + language;
	console.log("here")
	$.ajax({
		type: "GET",
		dataType: "json",
		url: url,
		beforeSend: function() {
		    $(".entityshape-spinner").show();
		    console.log("before")
		},
		success: function(data){
		    console.log("success")
			let html = "";
			for (let i = 0; i < data.schema.length; i++ ) {
                if (data.properties[i]) {
                    for (let key in data.properties[i]) {
                       let response1 = data.properties[i][key].response;
                       let response_class  = "";
                        switch (response1) {
                            case "present":
                                response_class = "present";
                                break;
                            case "correct":
                                response_class = "correct";
                                break;
                            case "missing":
                                response_class = "missing";
                                break;
                            default:
                                response_class = "wrong";
                                break;
                        }
                        if (data.properties[i][key].necessity == "absent") {
                            if (response1 == "too many statements") {
                                response1 = "not allowed";
                            }
                        }
                        if (!response1) {
                            response1 = "Not in schema";
                            response_class = "notinschema";
                        }
                        if (response1 == null) {
                            response1 = "Not in schema";
                            response_class = "notinschema";
                        }
                        if ($("#" + key)[0]) {
                            $("#" + key + " .wikibase-statementgroupview-property-label").append("<br class='entityschema-property'/><div style='display:inline-block;' class='entityschema-span entityschema-property entityschema-" + response_class + "' title='" + data.schema[i] + ": " + data.name[i] + "'>" + data.schema[i] + ": " + response1 + "</div>");
                        }
                    }
                }

                if (data.statements[i]) {
                    for (let statement in data.statements[i]) {
                        let response2 = data.statements[i][statement].response;
                        if (response2 != "not in schema") {
                            html = "<br class='entityschema-property'/><span class='entityschema-span entityschema-property entityschema-" + response2 + "'>" + data.schema[i] + ": " + response2 + "</span>";
                            $("div[id='" + statement + "'] .wikibase-toolbar-button-edit").append(html);
                        }
                    }
                }
                if (data.general[i]) {
                    if (data.general[i].language) {
                        let response3 = data.general[i].language;
                        if (response3 != "not in schema") {
                            html = "<span class='entityschema-property'/><span class='entityschema-span entityschema-property entityschema-" + response3 + "'>" + response3 + "</span>";
                            $("span[class='language-lexical-category-widget_language']").append(html);
                        }
                    }
                    if (data.general[i].lexicalCategory) {
                        let response4 = data.general[i].lexicalCategory;
                        if (response4 != "not in schema") {
                            html = "<span class='entityschema-property'/><span class='entityschema-span entityschema-property entityschema-" + response4 + "'>" + response4 + "</span>";
                            $("span[class='language-lexical-category-widget_lexical-category']").append(html);
                        }
                    }
                }
			}

			const combined_properties = {}
			for (let i = 0; i < data.schema.length; i++ ) {
                for (let key in data.properties[i]) {
                  if(!combined_properties.hasOwnProperty(key)){ combined_properties[key] = {}; }
                  combined_properties[key]["name"] = data.properties[i][key]["name"]
                  if(!combined_properties[key].hasOwnProperty("response")) { combined_properties[key]["response"] = {}; }
                  combined_properties[key]["response"][data.schema[i]] = data.properties[i][key]["response"]
                  if(!combined_properties[key].hasOwnProperty("necessity")) { combined_properties[key]["necessity"] = {}; }
                  combined_properties[key]["necessity"][data.schema[i]] = data.properties[i][key]["necessity"]
                }
			}

			for (let key in combined_properties) {
			    let necessity = "absent"
			    let response = ""
			    let response_key = combined_properties[key]["response"]
                let necessity_key = combined_properties[key]["necessity"]

			    if (Object.values(necessity_key).includes("required")) {
			        necessity = "required";
			    } else if (Object.values(necessity_key).includes("optional")) {
			        necessity = "optional";
			    }

			    if (Object.values(response_key).includes("incorrect")) {
                     response = "incorrect";
                } else if (Object.values(response_key).includes("missing")) {
                     response = "missing";
                } else if (Object.values(response_key).includes("too many statements")) {
                     response = "too many statements";
                } else if (Object.values(response_key).includes("not enough statements")) {
                     response = "not enough statements";
                } else if (Object.values(response_key).includes("correct")) {
                     response = "correct";
                } else if (Object.values(response_key).includes("present")) {
                     response = "present";
                } else if (Object.values(response_key).includes("allowed")) {
                     response = "present";
                }

			    combined_properties[key]["response"]["combined"] = response
			    combined_properties[key]["necessity"]["combined"] = necessity;
			}

            html += "<br/>Checking against <b>"
            for (let schema in data.schema) {
                html += "<a href='https://www.wikidata.org/wiki/EntitySchema:" + data.schema[schema] + "'>" + data.schema[schema] + ":" + data.name[schema] + '</a> '
            }
            html += '</b>:'

            html += '<div style="overflow-y: scroll; max-height:200px;"><table style="width:100%;">';
            html += '<th class="entityschema_table" title="Properties in this item which must be present">Required properties</th>';
            html += '<th class="entityschema_table" title="Properties in this item which can be present but do not have to be">Optional properties</th>';
            html += '<th class="entityschema_table" title="Properties in this item which are not allowed to be present or not mentioned in the entityschema">Other properties</th><tr>';

            let required_html = '<td class="entityschema_table required">';
            let optional_html = '<td class="entityschema_table optional">';
            let absent_html = '<td class="entityschema_table absent">';
            if (combined_properties) {
                for (let key in combined_properties) {
                    let shape_html = "";
                    let response1 = combined_properties[key].response.combined;
                    let response_class  = "";
                    switch (response1) {
                        case "present":
                            response_class = "present";
                            break;
                        case "allowed":
                            response_class = "present";
                            break;
                        case "correct":
                            response_class = "correct";
                            break;
                        case "missing":
                            response_class = "missing";
                            break;
                        default:
                            response_class = "wrong";
                            break;
                    }
                    if (combined_properties[key].necessity.combined == "absent") {
                        if (response1 == "too many statements") {
                            response1 = "not allowed";
                        }
                    }
                    if (!response1) {
                        response1 = "Not in schema";
                        response_class = "notinschema";
                    }
                    if (response1 == null) {
                        response1 = "";
                        shape_html += '<a href="https://www.wikidata.org/wiki/Property:' + key;
                        shape_html +='">'+ key + " - <small>" + combined_properties[key].name + '</small></a><br/>';
                    } else {
                        shape_html += '<span class="entityschema-span entityschema-' + response_class + '">' + response1 + '</span><a href="https://www.wikidata.org/wiki/Property:' + key;
                        shape_html +='" class="is_entityschema-'+ response_class+'">'+ key + " - <small>" + combined_properties[key].name + '</small></a><br/>';
                    }
                    switch (combined_properties[key].necessity.combined){
                        case "required":
                            required_html += shape_html;
                            break;
                        case "optional":
                            optional_html += shape_html;
                            break;
                        default:
                            absent_html += shape_html;
                            break;
                    }
                }
            }
            required_html += "</td>";
            optional_html += "</td>";
            absent_html += "</td>";
            html += required_html + optional_html + absent_html;
            html += '</tr></table></div>';

            $("#entityschemaResponse" ).append( html );
            $(".entityshape-spinner").hide();
		},
		error: function(data) {
			$("#entityschemaResponse").append( '<span>Unable to validate schema</span>' );
		}
	});
}

function entityschema_getStylesheet() {
	let stylesheet = "#entityschema-schemaSearchButton { background-position: center center; background-repeat: no-repeat; position: relative !important; top: 0; right: 0; overflow: hidden; height: 100%; background-color: #1E90FF !important; color: #FFFFFF !important; padding: 0.5em; text-indent: 0px !important; margin-left: 5px; width: 50px; margin-right: 5px;}";
	stylesheet += "#entityschema-entityToCheck { padding: 0.5em; margin: 0; width: 33%;}";
	stylesheet += ".response { padding: 2px;}";
	stylesheet += "a.is_entityschema-present { color: #008800; }";
	stylesheet += "a.is_entityschema-allowed { color: #008800; }";
	stylesheet += "a.is_entityschema-correct { color: #00CC00; }";
	stylesheet += "a.is_entityschema-missing { color: #FF5500; }";
	stylesheet += "a.is_entityschema-notinschema { color: #FF5500; }";
	stylesheet += "a.is_entityschema-wrong { color: #CC0000; }";
	stylesheet += "a.is_entityschema-wrong_amount { color: #CC0000; }";
	stylesheet += "a.is_entityschema-incorrect { color: #CC0000; }";
	stylesheet += ".entityschema_table {vertical-align: top; width: 33%;} ";
	stylesheet += ".entityschema-missing { background-color: #FF8C00; }";
	stylesheet += ".entityschema-notinschema { background-color: #FF8C00; }";
	stylesheet += ".entityschema-wrong { background-color: #CC0000; }";
	stylesheet += ".entityschema-incorrect { background-color: #CC0000; }";
	stylesheet += ".entityschema-wrong_amount { background-color: #CC0000; }";
	stylesheet += ".entityschema-excess { background-color: #CC0000; }";
	stylesheet += ".entityschema-deficit { background-color: #CC0000; }";
	stylesheet += ".entityschema-present { background-color: #008800; }";
	stylesheet += ".entityschema-allowed { background-color: #008800; }";
	stylesheet += ".entityschema-correct { background-color: #00CC00; }";
	stylesheet += ".required .entityschema-missing { background-color: #FF0000;}";
	stylesheet += ".required a.is_entityschema-missing { color: #FF0000;}";
	stylesheet += ".absent .entityschema-missing { display: none;}";
	stylesheet += ".absent a.is_entityschema-missing { display: none;}";
	stylesheet += ".entityschema-span { color: #ffffff; padding:2px; margin: 2px; font-size:75%; border-radius:2px; }";
	stylesheet += ".entityshape-spinner,.entityshape-spinner div,.entityshape-spinner div:after {box-sizing: border-box;}"
	stylesheet += ".entityshape-spinner { padding-top:5px; padding-bottom:5px; color: currentColor; display: inline-block; position: relative; width: 20px; height: 20px;}"
	stylesheet += ".entityshape-spinner div { transform-origin: 10px 10px; animation: entityshape-spinner 1.2s linear infinite;}"
	stylesheet += '.entityshape-spinner div:after { content: " "; display: block; position: absolute; top: 0.8px; left: 9.2px; width: 1.6px; height: 4.4px; border-radius: 20%; background: currentColor;}'
	stylesheet += ".entityshape-spinner div:nth-child(1) { transform: rotate(0deg); animation-delay: -1.1s;}"
	stylesheet += ".entityshape-spinner div:nth-child(2) { transform: rotate(30deg); animation-delay: -1s;}"
	stylesheet += ".entityshape-spinner div:nth-child(3) { transform: rotate(60deg); animation-delay: -0.9s;}"
	stylesheet += ".entityshape-spinner div:nth-child(4) { transform: rotate(90deg); animation-delay: -0.8s;}"
	stylesheet += ".entityshape-spinner div:nth-child(5) { transform: rotate(120deg); animation-delay: -0.7s;}"
	stylesheet += ".entityshape-spinner div:nth-child(6) { transform: rotate(150deg); animation-delay: -0.6s;}"
	stylesheet += ".entityshape-spinner div:nth-child(7) { transform: rotate(180deg); animation-delay: -0.5s;}"
	stylesheet += ".entityshape-spinner div:nth-child(8) { transform: rotate(210deg); animation-delay: -0.4s;}"
	stylesheet += ".entityshape-spinner div:nth-child(9) { transform: rotate(240deg); animation-delay: -0.3s;}"
	stylesheet += ".entityshape-spinner div:nth-child(10) { transform: rotate(270deg); animation-delay: -0.2s;}"
	stylesheet += ".entityshape-spinner div:nth-child(11) { transform: rotate(300deg); animation-delay: -0.1s;}"
	stylesheet += ".entityshape-spinner div:nth-child(12) { transform: rotate(330deg); animation-delay: 0s;}"
	stylesheet += "@keyframes entityshape-spinner { 0% { opacity: 1; } 100% { opacity: 0; }}"
	return stylesheet;
}
}());
