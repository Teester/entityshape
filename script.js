(function() {
let entityschema_stylesheet = entityschema_getStylesheet();
$('html > head').append("<style>" + entityschema_stylesheet + "</style>");

$(document).ready(function(){
	let entityID = mw.config.get( 'wbEntityId' );
	let lang = mw.config.get( 'wgUserLanguage' );
	if (entityID) {
		let schema = window.localStorage.getItem("entityschema");
		let value = window.localStorage.getItem("entityschema-auto");
		let entityschema_entityName = document.location.pathname.substring(6);
		if (value == "true") {
			entityschema_checkEntity(entityschema_entityName, schema, lang);
			$("#entityschema-checkbox").prop('checked', true);
		} else {
			$("#entityschema-checkbox").prop('checked', false);
		}
		$("#entityschema-entityToCheck:text").val(schema);
	}
});

let entityschema_conditions = ["/wiki/Q", "/wiki/P", "/wiki/L"];
if (entityschema_conditions.some(el => document.location.pathname.includes(el))) {
	let entityschema_entity_html = '<div><span id="entityschema-simpleSearch"><span>';
	entityschema_entity_html += '<input type="text" id="entityschema-entityToCheck" placeholder="Enter a schema to check against e.g. E234">';
	entityschema_entity_html += '<input type="submit" id="entityschema-schemaSearchButton" class="searchButton" name="check" value="Check">';
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
	let entityschema_entityName = document.location.pathname.substring(6);
	let lang = mw.config.get( 'wgUserLanguage' );
	window.localStorage.setItem("entityschema", entityschema_entitySchema);
	entityschema_checkEntity(entityschema_entityName, entityschema_entitySchema, lang);
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
	let url = "https://entityshape.toolforge.org/api/v2?entityschema=" + entitySchema + "&entity=" + entity + "&language=" + language;
	//let url = "http://127.0.0.1:5000/api/v2?entityschema=" + entitySchema + "&entity=" + entity + "&language=" + language;
	$.ajax({
		type: "GET",
		dataType: "json",
		url: url,
		success: function(data){
			let html = "";
			for (var i = 0; i < data.schema.length; i++ ) {
                html += "<br/>Checking against <b><a href='https://www.wikidata.org/wiki/EntitySchema:" + data.schema[i] + "'>" + data.schema[i] + ":" + data.name[i] + '</a></b>:';
                if (data.validity.results) {
                    if (data.validity.results[0].result) {
                        html += '<span class="response"><span class="pass">✔</span><span> Pass</span></span><br/>';
                    } else {
                        html += entityschema_parseResult(data.validity.results[0]);
                    }
                }
                html += '<div style="overflow-y: scroll; max-height:200px;"><table style="width:100%;">';
                html += '<th class="entityschema_table" title="Properties in this item which must be present">Required properties</th>';
                html += '<th class="entityschema_table" title="Properties in this item which can be present but do not have to be">Optional properties</th>';
                html += '<th class="entityschema_table" title="Properties in this item which are not allowed to be present or not mentioned in the entityschema">Other properties</th><tr>';

                let required_html = '<td class="entityschema_table required">';
                let optional_html = '<td class="entityschema_table optional">';
                let absent_html = '<td class="entityschema_table absent">';
                if (data.properties[i]) {
                    for (let key in data.properties[i]) {
                        let shape_html = "";
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
                            response1 = "";
                            shape_html += '<a href="https://www.wikidata.org/wiki/Property:' + key;
                            shape_html +='">'+ key + " - <small>" + data.properties[i][key].name + '</small></a><br/>';
                        } else {
                            shape_html += '<span class="entityschema-span entityschema-' + response_class + '">' + response1 + '</span><a href="https://www.wikidata.org/wiki/Property:' + key;
                            shape_html +='" class="is_entityschema-'+ response_class+'">'+ key + " - <small>" + data.properties[i][key].name + '</small></a><br/>';
                        }
                        switch (data.properties[i][key].necessity){
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
                        if ($("#" + key)[0]) {
                            $("#" + key + " .wikibase-statementgroupview-property-label").append("<br class='entityschema-property'/><div style='display:inline-block;' class='entityschema-span entityschema-property entityschema-" + response_class + "' title='" + data.schema[i] + ": " + data.name[i] + "'>" + data.schema[i] + ": " + response1 + "</div>");
                        }
                    }
                }
                required_html += "</td>";
                optional_html += "</td>";
                absent_html += "</td>";
                html += required_html + optional_html + absent_html;
                html += '</tr></table></div>';

                $("#entityschemaResponse" ).append( html );

                if (data.statements[i]) {
                    for (var statement in data.statements[i]) {
                        let response2 = data.statements[i][statement].response;
                        if (response2 != "not in schema") {
                            html = "<br class='entityschema-property'/><span class='entityschema-span entityschema-property entityschema-" + response2 + "'>" + response2 + "</span>";
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
		},
		error: function(data) {
			$("#entityschemaResponse").append( '<span>Unable to validate schema</span>' );
		}
	});
}

function entityschema_parseResult(data) {
	let property = [];
	let html = '<span class="response" title="' + data.reason + '"><span class="fail">✘</span><span class="response"> Fail</span>';
	let no_matching_triples = "No matching triples found for predicate";
	if (data.reason.includes(no_matching_triples)) {
		property = data.reason.match(/P\d+/g);
	}
	if (property !== null) {
		property = property.reduce(function(a,b) {
		        if (a.indexOf(b) < 0) {
		            a.push(b);
		        }
		        return a;
		    },[]);
		for (let i = 0; i < property.length; i++) {
			if (property[i].length > 100) {
				property[i] = property[i].substr(0,100) + "…"
			}
			html += '<span class="missing"> Missing valid ' + property[i] + '</span>';
		}
	}
	html += "</span>";
	return html;
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
	return stylesheet;
}
}());
