/*
 * Example plugin template
 */

jsPsych.plugins["debrief"] = (function() {

    var plugin = {};

    plugin.info = {
        name: "debrief",
        parameters: {
            display: {
                type: jsPsych.plugins.parameterType.OBJECT,
                default: undefined
            }
        }
    }


    plugin.trial = function(display_element, trial) {

        var data = jsPsych.data.get().values();



        for (var i = 0; i < trial.display.length; i++){
            trial.display[i](data, display_element);
        }

        // data saving
        var trial_data = {
        };

        // end trial
        jsPsych.finishTrial(trial_data);
    };

    return plugin;
})();
