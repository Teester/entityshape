(function() {
let entitycheck_stylesheet = entitycheck_getStylesheet();
$('html > head').append("<style>" + entitycheck_stylesheet + "</style>");

$(document).ready(function(){
	let entityID = mw.config.get( 'wbEntityId' );
	let lang = mw.config.get( 'wgUserLanguage' );
	if (entityID) {
		let schema = window.localStorage.getItem("entitycheck");
		let value = window.localStorage.getItem("entitycheck-auto");
		let entitycheck_entityName = document.location.pathname.substring(6);
		if (value == "true") {
			entitycheck_checkEntity(entitycheck_entityName, schema, lang);
			$("#entitycheck-checkbox").prop('checked', true);
		} else {
			$("#entitycheck-checkbox").prop('checked', false);
		}
		$("#entityschema-entityToCheck:text").val(schema);
	}
});

let entitycheck_conditions = ["/wiki/Q", "/wiki/P", "/wiki/L"];
if (entitycheck_conditions.some(el => document.location.pathname.includes(el))) {
	let entitycheck_entity_html = '<div><span id="entityschema-simpleSearch"><span>';
	entitycheck_entity_html += '<input type="text" id="entityschema-entityToCheck" placeholder="Enter a schema to check against e.g. E234">';
	entitycheck_entity_html += '<input type="submit" id="entityschema-schemaSearchButton" class="searchButton" name="check" value="Check">';
	entitycheck_entity_html += '</span></span><input type="checkbox" id="entitycheck-checkbox">';
	entitycheck_entity_html += '<label for="entitycheck-checkbox"><small>Automatically check schema</small></label><span id="entityCheckResponse"></span></div>';
	var entitycheck_entityTitle = $(".wikibase-title-id" )[0].innerText;
	if (document.location.pathname.includes("/wiki/L")) {
		$(".mw-indicators" ).append( entitycheck_entity_html );
	} else {
		$(".wikibase-entitytermsview-heading" ).append( entitycheck_entity_html );
	}
	$("#entityschema-schemaSearchButton").click(function(){ entitycheck_update() });
	$("#entitycheck-checkbox").click(function() { entitycheck_checkbox() })
}

$("#entityschema-entityToCheck").on("keyup", function(event){
	if (event.key === "Enter") {
		event.preventDefault();
		$("#entityschema-schemaSearchButton").click();
		return false;
	}
});

function entitycheck_update() {
	let entitycheck_entitySchema = $("#entityschema-entityToCheck")[0].value.toUpperCase();
	let entitycheck_entityName = document.location.pathname.substring(6);
	let lang = mw.config.get( 'wgUserLanguage' );
	window.localStorage.setItem("entitycheck", entitycheck_entitySchema);
	entitycheck_checkEntity(entitycheck_entityName, entitycheck_entitySchema, lang);
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
	$(".entitycheck-property").remove();
	let url = "https://entityshape.toolforge.org/api?entityschema=" + entitySchema + "&entity=" + entity + "&language=" + language;
	$.ajax({
		type: "GET",
		dataType: "json",
		url: url,
		success: function(data){
			let html = "";

			html += "<br/>Checking against <b><a href='https://www.wikidata.org/wiki/EntitySchema:" + data.schema + "'>" + data.schema + ":" + data.name + '</a></b>:';
			if (data.validity.results) {
				if (data.validity.results[0].result) {
					html += '<span class="response"><span class="pass">✔</span><span> Pass</span></span><br/>';
				} else {
					html += entitycheck_parseResult(data.validity.results[0]);
				}
			}
			html += '<div style="overflow-y: scroll; max-height:200px;"><table style="width:100%;">';
			html += '<th class="entitycheck_table" title="Properties in this item which must be present">Required properties</th>';
			html += '<th class="entitycheck_table" title="Properties in this item which can be present but do not have to be">Optional properties</th>';
			html += '<th class="entitycheck_table" title="Properties in this item which are not allowed to be present or not mentioned in the entityschema">Other properties</th><tr>';

			let required_html = '<td class="entitycheck_table required">';
			let optional_html = '<td class="entitycheck_table optional">';
			let absent_html = '<td class="entitycheck_table absent">';
			if (data.properties) {
				for (let key in data.properties) {
					let shape_html = "";
					let response1 = data.properties[key].response;
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
					if (data.properties[key].necessity == "absent") {
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
						shape_html +='">'+ key + " - <small>" + data.properties[key].name + '</small></a><br/>';
					} else {
						shape_html += '<span class="entitycheck-span entitycheck-' + response_class + '">' + response1 + '</span><a href="https://www.wikidata.org/wiki/Property:' + key;
						shape_html +='" class="is_entitycheck-'+ response_class+'">'+ key + " - <small>" + data.properties[key].name + '</small></a><br/>';
					}
					switch (data.properties[key].necessity){
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
						$("#" + key + " .wikibase-statementgroupview-property-label").append("<br class='entitycheck-property'/><div style='display:inline-block;' class='entitycheck-span entitycheck-property entitycheck-" + response_class + "' title='" + data.schema + ": " + data.name + "'>" + data.schema + ": " + response1 + "</div>");
					}
				}
			}
			required_html += "</td>";
			optional_html += "</td>";
			absent_html += "</td>";
			html += required_html + optional_html + absent_html;
			html += '</tr></table></div>';

			$("#entityCheckResponse" ).append( html );

			if (data.statements) {
				for (var statement in data.statements) {
					let response2 = data.statements[statement].response;
					if (response2 != "not in schema") {
						html = "<br class='entitycheck-property'/><span class='entitycheck-span entitycheck-property entitycheck-" + response2 + "'>" + response2 + "</span>";
						$("div[id='" + statement + "'] .wikibase-toolbar-button-edit").append(html);
					}
				}
			}
			if (data.general) {
			    if (data.general.language) {
			    	let response3 = data.general.language;
                    if (response3 != "not in schema") {
                        html = "<span class='entitycheck-property'/><span class='entitycheck-span entitycheck-property entitycheck-" + response3 + "'>" + response3 + "</span>";
                        $("span[class='language-lexical-category-widget_language']").append(html);
                    }
			    }
                if (data.general.lexicalCategory) {
                    let response4 = data.general.lexicalCategory;
                    if (response4 != "not in schema") {
                        html = "<span class='entitycheck-property'/><span class='entitycheck-span entitycheck-property entitycheck-" + response4 + "'>" + response4 + "</span>";
                        $("span[class='language-lexical-category-widget_lexical-category']").append(html);
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

function entitycheck_getStylesheet() {
	let stylesheet = "#schemaSearchButton { background-position: center center; background-repeat: no-repeat; position: absolute; top:0; right:0; overflow: hidden; height:100%; background-color: #1E90FF !important; color: #FFFFFF !important; padding: 2px !important}";
	stylesheet += "#entityToCheck { padding: 1em; margin:0; width: 100%;}";
	stylesheet += ".response { padding: 2px;}";
	stylesheet += "a.is_entitycheck-present { color: #008800; }";
	stylesheet += "a.is_entitycheck-allowed { color: #008800; }";
	stylesheet += "a.is_entitycheck-correct { color: #00CC00; }";
	stylesheet += "a.is_entitycheck-missing { color: #FF5500; }";
	stylesheet += "a.is_entitycheck-notinschema { color: #FF5500; }";
	stylesheet += "a.is_entitycheck-wrong { color: #CC0000; }";
	stylesheet += "a.is_entitycheck-wrong_amount { color: #CC0000; }";
	stylesheet += "a.is_entitycheck-incorrect { color: #CC0000; }";
	stylesheet += ".entitycheck_table {vertical-align: top; width: 33%;} ";
	stylesheet += ".entitycheck-missing { background-color: #FF8C00; }";
	stylesheet += ".entitycheck-notinschema { background-color: #FF8C00; }";
	stylesheet += ".entitycheck-wrong { background-color: #CC0000; }";
	stylesheet += ".entitycheck-incorrect { background-color: #CC0000; }";
	stylesheet += ".entitycheck-wrong_amount { background-color: #CC0000; }";
	stylesheet += ".entitycheck-excess { background-color: #CC0000; }";
	stylesheet += ".entitycheck-deficit { background-color: #CC0000; }";
	stylesheet += ".entitycheck-present { background-color: #008800; }";
	stylesheet += ".entitycheck-allowed { background-color: #008800; }";
	stylesheet += ".entitycheck-correct { background-color: #00CC00; }";
	stylesheet += ".required .entitycheck-missing { background-color: #FF0000;}";
	stylesheet += ".required a.is_entitycheck-missing { color: #FF0000;}";
	stylesheet += ".absent .entitycheck-missing { display: none;}";
	stylesheet += ".absent a.is_entitycheck-missing { display: none;}";
	stylesheet += ".entitycheck-span { color: #ffffff; padding:2px; margin: 2px; font-size:75%; border-radius:2px; }";
	return stylesheet;
}
}());
