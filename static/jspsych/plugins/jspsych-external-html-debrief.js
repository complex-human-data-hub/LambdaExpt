/*

     debrief
     timeline.push({
         type: 'external-html-debrief',
         url: "{{url_for('static', filename='html/debrief-1.html')}}",
         set_params: [
             function(data, display_element){
                 //Set card game score
                 var tp = fn = fp = tn = 0;
                 for(var i = 0; i < data.length; i++){
                     item = data[i]; 
                     if(item['part'] == 'card_game'){
                         display_element.querySelector("#card_game_score").innerHTML = item['score'];
                         display_element.querySelector("#card_game_answers").innerHTML = item['guesses'];
                         display_element.querySelector("#card_game_cards").innerHTML = item['cards_viewed'];
                     }
                     
                     if(item['part'] == 'test_list'){
                         console.log(item);
                         var key = item['key_press'] == 89 ? true : false;
                         var intrial = item['intrial'] ;
                           if(intrial && key){
                             tp++;
                           }else if(intrial && !key){
                             fn++;
                           }else if(!intrial && key){
                             fp++;
                           }else if(!intrial && !key){
                             tn++;
                           }
                     }
                 }
                 // Set memory test score
                 var precision = parseInt( (tp / (tp+fp)) * 100, 10); 
                 var recall = parseInt( (tp / (tp+fn)) * 100, 10);
                 var accuracy = parseInt(  (( tp + tn ) / (tp + tn + fp + fn)) * 100, 10 );
                 
                 display_element.querySelector("#memory_precision").innerHTML = precision;
                 display_element.querySelector("#memory_recall").innerHTML = recall;
                 display_element.querySelector("#memory_accuracy").innerHTML = accuracy;

             }
         ],
         cont_btn: "next",
         data: {'part': 'debriefing'}

     });
     

*/

jsPsych.plugins['external-html-debrief'] = (function() {

    var plugin = {};

    plugin.info = {
        name: 'external-html-debrief',
        description: '',
        parameters: {
            url: {
                type: jsPsych.plugins.parameterType.STRING,
                pretty_name: 'URL',
                default: undefined,
                description: 'The url of the external html page'
            },
            cont_key: {
                type: jsPsych.plugins.parameterType.KEYCODE,
                pretty_name: 'Continue key',
                default: null,
                description: 'The key to continue to the next page.'
            },
            cont_btn: {
                type: jsPsych.plugins.parameterType.STRING,
                pretty_name: 'Continue button',
                default: null,
                description: 'The button to continue to the next page.'
            },
            check_fn: {
                type: jsPsych.plugins.parameterType.FUNCTION,
                pretty_name: 'Check function',
                default: function() { return true; },
                description: ''
            },
            set_params: {
                type: jsPsych.plugins.parameterType.FUNCTION,
                pretty_name: 'Set Params Function',
                default: function(data) { return true; },
                description: ''
            },
            force_refresh: {
                type: jsPsych.plugins.parameterType.BOOL,
                pretty_name: 'Force refresh',
                default: false,
                description: 'Refresh page.'
            }
        }
    }

    plugin.trial = function(display_element, trial) {

        var url = trial.url;
        if (trial.force_refresh) {
            url = trial.url + "?time=" + (new Date().getTime());
        }

        load(display_element, url, function() {
            var t0 = (new Date()).getTime();
            var finish = function() {
                if (trial.check_fn && !trial.check_fn(display_element)) { return };
                if (trial.cont_key) { document.removeEventListener('keydown', key_listener); }
                var trial_data = {
                    rt: (new Date()).getTime() - t0,
                    url: trial.url
                };
                display_element.innerHTML = '';
                jsPsych.finishTrial(trial_data);
            };
            if (trial.cont_btn) { display_element.querySelector('#'+trial.cont_btn).addEventListener('click', finish); }
            if (trial.set_params) {
                var data = jsPsych.data.get().values();
                for(var i = 0; i < trial.set_params.length; i++){
                    console.log(data);
                    trial.set_params[i](data, display_element);
                }
            }
            if (trial.cont_key) {
                var key_listener = function(e) {
                    if (e.which == trial.cont_key) finish();
                };
                display_element.addEventListener('keydown', key_listener);
            }
        });
    };

    // helper to load via XMLHttpRequest
    function load(element, file, callback){
        var xmlhttp = new XMLHttpRequest();
        xmlhttp.open("GET", file, true);
        xmlhttp.onload = function(){
            if(xmlhttp.status == 200 || xmlhttp.status == 0){ //Check if loaded
                element.innerHTML = xmlhttp.responseText;
                callback();
            }
        }
        xmlhttp.send();
    }

    return plugin;
})();
