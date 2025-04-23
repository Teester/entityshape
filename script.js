/**
 * EntityShape.js adds an input box to a wikidata page wherein you can enter an entityschema
 * (such as E10).  When you click "Check", checks whether each statement and property conforms
 * to the schema.  It then displays a summary at the top of the item for each property indicating
 * whether they conform or not.  It also adds a badge to each statement and each property on the
 * page indicating whether they conform or not.
 **/

(function() {
    "use strict";

    mw.util.addCSS(entityschema_getStylesheet());
    let entityschema_list = [];
    let value = mw.storage.get("entityschema-auto");
    let schema = mw.storage.get("entityschema");
    let property_list = [];
    let item_list = [];

    mw.hook( 'wikibase.entityPage.entityLoaded' ).add( function ( data ) {
        let valid_values = ['item', 'lexeme', 'property']
        if (!valid_values.includes(data["type"])) { return; }

        mw.util.addSubtitle(entityschema_getHTML());
        $("#entityschema-checkbox").prop('checked', value);
        $("#entityschema-schemaSearchButton").click(function(){ entityschema_update(); });
        $("#entityschema-checkbox").click(function() { entityschema_checkbox(); });

        let claims = data["claims"];
        for (let claim in claims) {
            property_list.push(claim);
            let statements = claims[claim];
            for (let statement in statements) {
                let mainsnak = statements[statement]["mainsnak"];
                if (mainsnak["datavalue"] && mainsnak["datatype"] == "wikibase-item") {
                    if (!property_list.includes(mainsnak["datavalue"]["value"]["id"])) {
                        property_list.push(mainsnak["datavalue"]["value"]["id"]);
                    }
                }
            }
        }
        check_entity_for_schemas(property_list);
    });

    mw.hook( 'wikibase.statement.saved' ).add( function ( data ) {
        if (value == "true") {
            entityschema_update();
        }
    });

    mw.hook( 'wikibase.statement.removed' ).add( function ( data ) {
        if (value == "true") {
            entityschema_update();
        }
    });

    function check_entity_for_schemas(entity_list) {
        const api = new mw.Api({'User-Agent': 'Userscript Entityshape by User:Teester'});
        for (let item in entity_list) {
            api.get({
                action: 'wbgetclaims',
                property: 'P12861',
                entity: entity_list[item],
                format: 'json'})
                .fail(function() { console.log("failed to get schemas") })
                .done(function(data) {
                    if (data["claims"].hasOwnProperty("P12861")) {
                        let claims = data["claims"]["P12861"];
                        for (let claim in claims) {
                            entityschema_list.push(claims[claim]["mainsnak"]["datavalue"]["value"]["id"]);
                        }
                    }
                });
        }
    }

    $(document).ajaxStop(function () {
        if (entityschema_list.length != 0) {
            $('#entityschema-entityToCheck').attr("placeholder", `Check against ${entityschema_list.join(", ")}`);
        }
        if (value == "true" && mw.config.get( 'wbEntityId' )) {
            entityschema_update();
        }
        $("#entityschema-entityToCheck:text").val(schema);
        $(this).unbind('ajaxStop');
    });

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
            entityschema_entitySchema = entityschema_list.join(", ");
            mw.storage.remove("entityschema");
        } else {
            mw.storage.set("entityschema", entityschema_entitySchema);
        }
        if (entityschema_entitySchema.length == 0) {
            let message = new OO.ui.MessageWidget( {type: 'error', inline: true,
                label: 'No schemas entered and could not automatically determine schemas to check'} );
            $("#entityschema-response").empty().prepend( message.$element );
        } else {
            let entityschema_entityName = document.location.pathname.substring(6);
            let lang = mw.config.get( 'wgUserLanguage' );
            entityschema_checkEntity(entityschema_entityName, entityschema_entitySchema, lang);
        }
    }

    function entityschema_checkbox() {
        if ($('#entityschema-checkbox').is(":checked")) {
            mw.storage.set("entityschema-auto", true);
        } else {
            mw.storage.set("entityschema-auto", false);
        }
    }

    function entityschema_checkEntity(entity, entitySchema, language) {
        $("#entityschema-response").contents().remove();
        $(".entityschema-property").remove();
        $(".entityschema-span").remove();

        let url = "https://entityshape.toolforge.org/api/v2?entityschema=" + entitySchema + "&entity=" + entity + "&language=" + language;
        // let url = "http://127.0.0.1:5000/api/v2 ?entityschema=" + entitySchema + "&entity=" + entity + "&language=" + language;
        $.ajax({
            type: "GET",
            dataType: "json",
            url: url,
            beforeSend: function() {
                $(".entityshape-spinner").show();
            },
            success: function(data){
                for (let i = 0; i < data.schema.length; i++ ) {
                    if (data.properties[i]) {
                        entityschema_add_to_properties(data.properties[i], data.schema[i], data.name[i]);
                    }
                    if (data.statements[i]) {
                        entityschema_add_to_statements(data.statements[i], data.schema[i], data.name[i]);
                    }
                    if (data.general[i]) {
                        entityschema_add_general(data.general[i]);
                    }
                }

                const combined_properties = entityschema_combine_properties(data.properties, data.schema);

                let message_data = [];
                for (let schema in data.schema) {
                    message_data.push(`<a href='https://www.wikidata.org/wiki/EntitySchema:${data.schema[schema]}'>
                                      ${data.name[schema]} <small>(${data.schema[schema]})</small></a>`);
                }
                let message = `Checking against ${message_data.join(', ')}:`;

                let message_widget = new OO.ui.MessageWidget( {type: 'notice', inline: true,
                                                        label: new OO.ui.HtmlSnippet( message )} );
                $("#entityschema-response" ).append( message_widget.$element );

                let html = `<div style="overflow-y: scroll; max-height:200px;">
                            <table style="width:100%;">
                            <th class="entityschema_table" title="Properties in this item which must be present">Required properties</th>
                            <th class="entityschema_table" title="Properties in this item which can be present but do not have to be">Optional properties</th>
                            <th class="entityschema_table" title="Properties in this item which are not allowed to be present or not mentioned in the entityschema">Other properties</th>
                            <tr>`;

                html += entityschema_process_combined_properties(combined_properties);

                $("#entityschema-response" ).append( html );
                $(".entityshape-spinner").hide();
            },
            error: function(data) {
                let message = new OO.ui.MessageWidget( {type: 'error', inline: true,
                                label: 'Unable to validate schema'} );
                $("#entityschema-response" ).append( message.$element );
                $(".entityshape-spinner").hide();
            }
        });
    }

    function entityschema_process_combined_properties(properties) {
        let required_html = '<td class="entityschema_table required"><ul style="list-style-type:none";>';
        let optional_html = '<td class="entityschema_table optional"><ul style="list-style-type:none";>';
        let absent_html = '<td class="entityschema_table absent"><ul style="list-style-type:none";>';
        let other_array = [];
        let other_array_names = [];
        for (let key in properties) {
            let shape_html = "";
            let response1 = properties[key].response.combined;
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
            if (properties[key].necessity.combined == "absent") {
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
                shape_html += `<a href="https://www.wikidata.org/wiki/Property:${key}">${key} - <small>${properties[key].name}</small></a><br/>`;
            } else if (response1 == "Not in schema") {
                other_array.push(key);
                other_array_names.push(properties[key].name);
            } else {
                shape_html += `<li class="is_entityschema-${response_class}">
                               <span class="entityschema-span entityschema-${response_class}">${response1}</span>
                               <a href="https://www.wikidata.org/wiki/Property:${key}"
                                  class="is_entityschema-${response_class}">
                               ${key} - <small>${properties[key].name}</small></a></li>`
            }
            switch (properties[key].necessity.combined) {
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
        let other_html = `<details><summary>${other_array.length} properties not in any schema checked</summary>
                          <ul style='list-style-type:none';>`;
        for (let item in other_array) {
            other_html += `<li><span class="entityschema-span entityschema-notinschema">Not in schema</span>
                               <a href="https://www.wikidata.org/wiki/Property:${other_array[item]}"
                                  class="is_entityschema-notinschema">${other_array[item]} - <small>${other_array_names[item]}</small></a></li>`;
        }
        other_html += "</ul></details>";
        absent_html += "</ul>" + other_html;
        required_html += "</ul></td>";
        optional_html += "</ul></td>";
        absent_html += "</td>";
        let html = required_html + optional_html + absent_html + '</tr></table></div>';
        return html;
    }

    function entityschema_add_to_properties(properties, schema, name) {
        for (let key in properties) {
           let response = properties[key].response;
           let response_class = "";
            switch (response) {
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
            if (properties[key].necessity == "absent") {
                if (response == "too many statements") {
                    response = "not allowed";
                }
            }
            if (!response) {
                response = "Not in schema";
                response_class = "notinschema";
            }
            if (response == null) {
                response = "Not in schema";
                response_class = "notinschema";
            }
            if (response != "Not in schema" && $("#" + key)[0]) {
                let html =`<br class='entityschema-property'/>
                           <div style='display:inline-block;'
                                class='entityschema-span entityschema-property entityschema-${response_class}'
                                title='${schema}: ${name}'>${schema}: ${response}
                           </div>`;
                $(`#${key} .wikibase-statementgroupview-property-label`).append(html);
            }
        }
    }

    function entityschema_add_to_statements(statements, schema, name) {
        for (let statement in statements) {
            let response = statements[statement].response;
            if (response != "not in schema") {
                let html = `<br class='entityschema-property'/>
                            <span class='entityschema-span entityschema-property entityschema-${response}'
                                  title='${schema}: ${name}'>${schema}: ${response}
                            </span>`;
                $(`div[id='${statement}'] .wikibase-toolbar-button-edit`).append(html);
            }
        }
    }

    function entityschema_add_general(general) {
        if (general.language) {
            entityschema_add_general_item("language", general.language);
        }
        if (general.lexicalCategory) {
            entityschema_add_general_item("lexical_category", general.lexicalCategory);
        }
    }

    function entityschema_add_general_item(general_type, response) {
        if (response != "not in schema") {
            html = `<span class='entityschema-property'/>
                    <span class='entityschema-span entityschema-property entityschema-${response}'>${response}
                    </span>`;
            $(`span[class='language-lexical-category-${general_type}']`).append(html);
        }
    }

    function entityschema_combine_properties(property, schema) {
        let combined_properties = {};
        for (let i = 0; i < schema.length; i++ ) {
            for (let key in property[i]) {
              if(!combined_properties.hasOwnProperty(key)){ combined_properties[key] = {}; }
              combined_properties[key]["name"] = property[i][key]["name"];
              if(!combined_properties[key].hasOwnProperty("response")) { combined_properties[key]["response"] = {}; }
              combined_properties[key]["response"][schema[i]] = property[i][key]["response"];
              if(!combined_properties[key].hasOwnProperty("necessity")) { combined_properties[key]["necessity"] = {}; }
              combined_properties[key]["necessity"][schema[i]] = property[i][key]["necessity"];
            }
        }
        for (let key in combined_properties) {
            let necessity = "absent";
            let response = "";
            let response_key = combined_properties[key]["response"];
            let necessity_key = combined_properties[key]["necessity"];

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
            combined_properties[key]["response"]["combined"] = response;
            combined_properties[key]["necessity"]["combined"] = necessity;
        }
        return combined_properties;
    }

    function entityschema_getStylesheet() {
        const entityschema_stylesheet = `#entityschema-simpleSearch { width:500px; }
                                         #entityschema-response { padding:5px; display: block; }
                                         .entityschema-summary  { color: var(--color-progressive,#0645ad); }
                                         a.is_entityschema-present { color: #008800; }
                                         a.is_entityschema-allowed { color: #008800; }
                                         a.is_entityschema-correct { color: #00CC00; }
                                         a.is_entityschema-missing { color: #FF5500; }
                                         a.is_entityschema-notinschema { color: #FF5500; }
                                         a.is_entityschema-wrong { color: #CC0000; }
                                         a.is_entityschema-wrong_amount { color: #CC0000; }
                                         a.is_entityschema-incorrect { color: #CC0000; }
                                         .entityschema_table {vertical-align: top; width: 33%; }
                                         .entityschema-missing { background-color: #FF8C00; }
                                         .entityschema-notinschema { background-color: #FF8C00; }
                                         .entityschema-wrong { background-color: #CC0000; }
                                         .entityschema-incorrect { background-color: #CC0000; }
                                         .entityschema-wrong_amount { background-color: #CC0000; }
                                         .entityschema-excess { background-color: #CC0000; }
                                         .entityschema-deficit { background-color: #CC0000; }
                                         .entityschema-present { background-color: #008800; }
                                         .entityschema-allowed { background-color: #008800; }
                                         .entityschema-correct { background-color: #00CC00; }
                                         .required .entityschema-missing { background-color: #FF0000;}
                                         .required a.is_entityschema-missing { color: #FF0000;}
                                         .absent .entityschema-missing { display: none;}
                                         .absent a.is_entityschema-missing { display: none;}
                                         .entityschema-span { color: #ffffff; padding:2px; margin: 2px; font-size:75%; border-radius:2px; }
                                         .entityshape-spinner,.entityshape-spinner div,.entityshape-spinner div:after {box-sizing: border-box;}
                                         .entityshape-spinner { padding-top:5px; padding-bottom:5px; color: currentColor; display: inline-block; position: relative; width: 20px; height: 20px;}
                                         .entityshape-spinner div { transform-origin: 10px 10px; animation: entityshape-spinner 1.2s linear infinite;}
                                         .entityshape-spinner div:after { content: " "; display: block; position: absolute; top: 0.8px; left: 9.2px; width: 1.6px; height: 4.4px; border-radius: 20%; background: currentColor;}
                                         .entityshape-spinner div:nth-child(1) { transform: rotate(0deg); animation-delay: -1.1s;}
                                         .entityshape-spinner div:nth-child(2) { transform: rotate(30deg); animation-delay: -1s;}
                                         .entityshape-spinner div:nth-child(3) { transform: rotate(60deg); animation-delay: -0.9s;}
                                         .entityshape-spinner div:nth-child(4) { transform: rotate(90deg); animation-delay: -0.8s;}
                                         .entityshape-spinner div:nth-child(5) { transform: rotate(120deg); animation-delay: -0.7s;}
                                         .entityshape-spinner div:nth-child(6) { transform: rotate(150deg); animation-delay: -0.6s;}
                                         .entityshape-spinner div:nth-child(7) { transform: rotate(180deg); animation-delay: -0.5s;}
                                         .entityshape-spinner div:nth-child(8) { transform: rotate(210deg); animation-delay: -0.4s;}
                                         .entityshape-spinner div:nth-child(9) { transform: rotate(240deg); animation-delay: -0.3s;}
                                         .entityshape-spinner div:nth-child(10) { transform: rotate(270deg); animation-delay: -0.2s;}
                                         .entityshape-spinner div:nth-child(11) { transform: rotate(300deg); animation-delay: -0.1s;}
                                         .entityshape-spinner div:nth-child(12) { transform: rotate(330deg); animation-delay: 0s;}
                                         @keyframes entityshape-spinner { 0% { opacity: 1; } 100% { opacity: 0; }}`
        return entityschema_stylesheet;
    }

    function entityschema_getHTML() {
        const entityschema_results_html = `<details open style='box-shadow: 0 1px var(--border-color-subtle,#c8ccd1);'>
                                           <summary class='entityschema-summary'>Check against entityschema</summary>
                                           <div class="oo-ui-layout oo-ui-horizontalLayout">
                                              <div class="oo-ui-layout oo-ui-fieldLayout oo-ui-fieldLayout-align-top oo-ui-actionFieldLayout">
                                                  <div class="oo-ui-fieldLayout-body">
                                                      <div id="entityschema-simpleSearch" class="oo-ui-fieldLayout-field">
                                                          <div class="oo-ui-actionFieldLayout-input">
                                                              <div class="oo-ui-widget oo-ui-widget-enabled oo-ui-inputWidget oo-ui-textInputWidget oo-ui-textInputWidget-type-text">
                                                                  <input type="text" tabindex="0" class="oo-ui-inputWidget-input" value="" id="entityschema-entityToCheck" placeholder="Enter schema to check against e.g. E234">
                                                              </div>
                                                          </div>
                                                          <span class="oo-ui-actionFieldLayout-button" id="entityschema-schemaSearchButton">
                                                              <span class="oo-ui-widget oo-ui-widget-enabled oo-ui-buttonElement oo-ui-buttonElement-framed oo-ui-labelElement oo-ui-buttonWidget">
                                                                  <a class="oo-ui-buttonElement-button" role="button" tabindex="0" rel="nofollow">
                                                                      <span class="oo-ui-labelElement-label">Check</span>
                                                                  </a>
                                                              </span>
                                                          </span>
                                                      </div>
                                                  </div>
                                              </div>
                                              <div class="entityshape-spinner" style="display:none"><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div></div>
                                              <div class="oo-ui-layout oo-ui-labelElement oo-ui-fieldLayout oo-ui-fieldLayout-align-inline">
                                                  <div class="oo-ui-fieldLayout-body">
                                                      <span class="oo-ui-fieldLayout-field">
                                                          <span class="oo-ui-widget oo-ui-widget-enabled oo-ui-inputWidget oo-ui-checkboxInputWidget">
                                                              <input type="checkbox" tabindex="0" class="oo-ui-inputWidget-input" value="" id="entityschema-checkbox">
                                                              <span class="oo-ui-checkboxInputWidget-checkIcon oo-ui-widget oo-ui-widget-enabled oo-ui-iconElement oo-ui-iconElement-icon oo-ui-icon-check oo-ui-labelElement-invisible oo-ui-iconWidget oo-ui-image-invert">
                                                              </span>
                                                          </span>
                                                      </span>
                                                      <span class="oo-ui-fieldLayout-header">
                                                          <label class="oo-ui-labelElement-label">Automatically check schema</label>
                                                      </span>
                                                  </div>
                                              </div>
                                          </div>
                                          <span id="entityschema-response"></span></details>`
        return entityschema_results_html;
    }
}());