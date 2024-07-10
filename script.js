/**
 * EntityShape.js adds an input box to a wikidata page wherein you can enter an entityschema
 * (such as E10).  When you click "Check", checks whether each statement and property conforms
 * to the schema.  It then displays a summary at the top of the item for each property indicating
 * whether they conform or not.  It also adds a badge to each statement and each property on the
 * page indicating whether they conform or not.
 **/

(function() {
    mw.util.addCSS(entityschema_getStylesheet());
    let entityschema_list = [];
    let value = window.localStorage.getItem("entityschema-auto");
    let schema = window.localStorage.getItem("entityschema");
    let property_list = [];
    let item_list = [];
    let entityID = mw.config.get( 'wbEntityId' );

    $(document).ready(function(){
        if (value == "true") {
            $("#entityschema-checkbox").prop('checked', true);
        } else {
            $("#entityschema-checkbox").prop('checked', false);
        }
        let entityschema_conditions = ["/wiki/Q", "/wiki/P", "/wiki/L"];
        if (entityschema_conditions.some(el => document.location.pathname.includes(el))) {
            let entityschema_entity_html = `<div><span id="entityschema-simpleSearch">
                                            <span>
                                            <input type="text" id="entityschema-entityToCheck"
                                                   placeholder="Enter schema to check against e.g. E234"
                                                   title="Enter 1 or more schemas to check against separated by commas e.g. E10, E236 or press Check to auto-determine schemas to check">
                                            <input type="submit" id="entityschema-schemaSearchButton"
                                                   class="searchButton" name="check" value="Check">
                                            <div class="entityshape-spinner" style="display:none"><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div></div>
                                            </span>
                                            </span><input type="checkbox" id="entityschema-checkbox">
                                            <label for="entityschema-checkbox"><small>Automatically check schema</small></label>
                                            <span id="entityschemaResponse"></span></div>`;
            $(entityschema_entity_html).insertAfter("#siteSub");
            $("#entityschema-schemaSearchButton").click(function(){ entityschema_update(); });
            $("#entityschema-checkbox").click(function() { entityschema_checkbox(); });
        }
    });

    mw.hook( 'wikibase.entityPage.entityLoaded' ).add( function ( data ) {
        let claims = data["claims"];
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
        check_entity_for_schemas(item_list);
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
            window.localStorage.setItem("entityschema", "");
        } else {
            window.localStorage.setItem("entityschema", entityschema_entitySchema);
        }
        if (entityschema_entitySchema.length == 0) {
            $("#entityschemaResponse").append( '<br/><span>No schemas entered and could not automatically determine schemas to check</span>' );
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
        $.ajax({
            type: "GET",
            dataType: "json",
            url: url,
            beforeSend: function() {
                $(".entityshape-spinner").show();
            },
            success: function(data){
                let html = "";
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

                html += "<br/>Checking against <b>";
                for (let schema in data.schema) {
                    html += `<a href='https://www.wikidata.org/wiki/EntitySchema:${data.schema[schema]}'>${data.schema[schema]}: ${data.name[schema]}</a> `;
                }
                html += `</b>:
                         <div style="overflow-y: scroll; max-height:200px;">
                         <table style="width:100%;">
                         <th class="entityschema_table" title="Properties in this item which must be present">Required properties</th>
                         <th class="entityschema_table" title="Properties in this item which can be present but do not have to be">Optional properties</th>
                         <th class="entityschema_table" title="Properties in this item which are not allowed to be present or not mentioned in the entityschema">Other properties</th>
                         <tr>`;

                html += entityschema_process_combined_properties(combined_properties);

                $("#entityschemaResponse" ).append( html );
                $(".entityshape-spinner").hide();
            },
            error: function(data) {
                $("#entityschemaResponse").append( '<br/><span>Unable to validate schema</span>' );
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
        html = required_html + optional_html + absent_html + '</tr></table></div>';
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
        stylesheet += ".entityshape-spinner,.entityshape-spinner div,.entityshape-spinner div:after {box-sizing: border-box;}";
        stylesheet += ".entityshape-spinner { padding-top:5px; padding-bottom:5px; color: currentColor; display: inline-block; position: relative; width: 20px; height: 20px;}";
        stylesheet += ".entityshape-spinner div { transform-origin: 10px 10px; animation: entityshape-spinner 1.2s linear infinite;}";
        stylesheet += '.entityshape-spinner div:after { content: " "; display: block; position: absolute; top: 0.8px; left: 9.2px; width: 1.6px; height: 4.4px; border-radius: 20%; background: currentColor;}';
        stylesheet += ".entityshape-spinner div:nth-child(1) { transform: rotate(0deg); animation-delay: -1.1s;}";
        stylesheet += ".entityshape-spinner div:nth-child(2) { transform: rotate(30deg); animation-delay: -1s;}";
        stylesheet += ".entityshape-spinner div:nth-child(3) { transform: rotate(60deg); animation-delay: -0.9s;}";
        stylesheet += ".entityshape-spinner div:nth-child(4) { transform: rotate(90deg); animation-delay: -0.8s;}";
        stylesheet += ".entityshape-spinner div:nth-child(5) { transform: rotate(120deg); animation-delay: -0.7s;}";
        stylesheet += ".entityshape-spinner div:nth-child(6) { transform: rotate(150deg); animation-delay: -0.6s;}";
        stylesheet += ".entityshape-spinner div:nth-child(7) { transform: rotate(180deg); animation-delay: -0.5s;}";
        stylesheet += ".entityshape-spinner div:nth-child(8) { transform: rotate(210deg); animation-delay: -0.4s;}";
        stylesheet += ".entityshape-spinner div:nth-child(9) { transform: rotate(240deg); animation-delay: -0.3s;}";
        stylesheet += ".entityshape-spinner div:nth-child(10) { transform: rotate(270deg); animation-delay: -0.2s;}";
        stylesheet += ".entityshape-spinner div:nth-child(11) { transform: rotate(300deg); animation-delay: -0.1s;}";
        stylesheet += ".entityshape-spinner div:nth-child(12) { transform: rotate(330deg); animation-delay: 0s;}";
        stylesheet += "@keyframes entityshape-spinner { 0% { opacity: 1; } 100% { opacity: 0; }}";
        return stylesheet;
    }
}());