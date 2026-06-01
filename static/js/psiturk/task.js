/*
 * task.js — psiTurk word-list memory experiment for LambdaExpt.
 *
 * This is the psiTurk-stack equivalent of templates/exp.html. Same input
 * (expt_data.study_list, expt_data.test_list, expt_data.study_document_order
 * — set server-side by expt_config.get_data()); same final S3 result shape.
 *
 * Flow:
 *   PLS → consent → instructions
 *     → 3 × (document + comprehension questions)
 *     → Study (each study_list word for ~2 s, auto-advance)
 *     → Test  (each test_list word: Y / N keypress)
 *     → Demographics
 *     → Save + Debrief (PUT /sync/<uid>, then form-POST /debrief)
 *
 * Researchers replace this file with their own. Keep the
 *   `currentview = NextPhase()`
 * pattern at the bottom of each phase so phases chain cleanly.
 *
 * `expt_data`, `uniqueId`, `condition`, `counterbalance`, `adServerLoc`,
 * `STATIC_DIR`, `_uid`, `_mturk`, `_prolific`, `send_debrief()` are all
 * defined in templates/exp-psiturk.html and templates/experiment_wrapper.html.
 */


/* -- DATA ----------------------------------------------------------------- */

var study_list = expt_data.study_list;
var test_list  = expt_data.test_list;
var study_document_order = expt_data.study_document_order || [0, 1, 2];

// Mirror exp.html — tag each test word with whether it was in the study list.
(function tagTestIntrial(){
    var seen = {};
    for(var i = 0; i < study_list.length; i++){
        seen[study_list[i].token] = true;
    }
    for(var i = 0; i < test_list.length; i++){
        test_list[i].intrial = !!seen[test_list[i].token];
    }
})();

// Documents + comprehension questions. Same shape as exp.html:206-302.
// .url points to the existing static/html/document-N.html files, which are
// SHARED with the jsPsych path — edit the document content there and both
// stacks pick up the change. Customise the prompts/options below.
var study_documents = [
    {
        url: STATIC_DIR + 'html/document-1.html',
        questions: [
            { prompt: "Lorem ipsum dolor sit amet?",
              options: ["Etiam ac dolor ornare, efficitur tortor nec, dapibus ligula.",
                        "Morbi porta est id iaculis auctor.",
                        "Nam malesuada sapien velit."] },
            { prompt: "Aliquam vehicula tristique augue, at tincidunt diam eleifend id?",
              options: ["Duis erat turpis, tincidunt ac diam id, malesuada tincidunt dolor",
                        "Suspendisse ante sem, suscipit in sagittis id, ornare sed lacus.",
                        "Sed nibh magna, rutrum non sapien in, commodo gravida libero."] }
        ]
    },
    {
        url: STATIC_DIR + 'html/document-2.html',
        questions: [
            { prompt: "Lorem ipsum dolor sit amet?",
              options: ["Etiam ac dolor ornare, efficitur tortor nec, dapibus ligula.",
                        "Morbi porta est id iaculis auctor.",
                        "Nam malesuada sapien velit."] },
            { prompt: "Aliquam vehicula tristique augue, at tincidunt diam eleifend id?",
              options: ["Duis erat turpis, tincidunt ac diam id, malesuada tincidunt dolor",
                        "Suspendisse ante sem, suscipit in sagittis id, ornare sed lacus.",
                        "Sed nibh magna, rutrum non sapien in, commodo gravida libero."] }
        ]
    },
    {
        url: STATIC_DIR + 'html/document-3.html',
        questions: [
            { prompt: "Lorem ipsum dolor sit amet?",
              options: ["Etiam ac dolor ornare, efficitur tortor nec, dapibus ligula.",
                        "Morbi porta est id iaculis auctor.",
                        "Nam malesuada sapien velit."] },
            { prompt: "Aliquam vehicula tristique augue, at tincidunt diam eleifend id?",
              options: ["Duis erat turpis, tincidunt ac diam id, malesuada tincidunt dolor",
                        "Suspendisse ante sem, suscipit in sagittis id, ornare sed lacus.",
                        "Sed nibh magna, rutrum non sapien in, commodo gravida libero."] }
        ]
    }
];


/* -- INIT ----------------------------------------------------------------- */

// uniqueId / adServerLoc / mode are set in templates/exp-psiturk.html.
var psiTurk = new PsiTurk(uniqueId, adServerLoc, mode);

// Record condition info in the unstructured-data bucket. Rescued server-side
// into the trial array via the `questiondata` trick — see experiment.py.
psiTurk.recordUnstructuredData('condition', condition);
psiTurk.recordUnstructuredData('counterbalance', counterbalance);

// Preload the pages we'll showPage() through, so trial transitions don't
// pay HTTP latency. preloadPages returns a Promise.
var pages = [
    STATIC_DIR + 'html/psiturk/plain-language-statement.html',
    STATIC_DIR + 'html/psiturk/consent.html',
    STATIC_DIR + 'html/psiturk/instructions.html',
    STATIC_DIR + 'html/psiturk/comprehension.html',
    STATIC_DIR + 'html/psiturk/stage.html',
    STATIC_DIR + 'html/psiturk/demographics.html'
];
study_documents.forEach(function(d){ pages.push(d.url); });

var init = (async () => { await psiTurk.preloadPages(pages); })();


/* -- PHASES --------------------------------------------------------------- */

// Each phase is a constructor function. Call showPage(), wire events, then
// on completion `currentview = NextPhase()`.
var currentview;


// DocsAndComprehension: for each doc in study_document_order, show the
// document, then on Next show the comprehension survey, capture answers,
// advance. After the last doc, → Study.
var DocsAndComprehension = function() {
    var i = 0;

    var showDoc = function() {
        if (i >= study_document_order.length) {
            currentview = Study();
            return;
        }
        var doc = study_documents[study_document_order[i]];
        psiTurk.showPage(doc.url);
        psiTurk.recordTrialData({phase: 'view_document', doc_n: study_document_order[i]});
        // document-N.html uses the jsPsych #next button id (it's shared
        // with the jsPsych path). Bind directly here — doInstructions
        // can't carry survey state between pages, so we're outside its scope.
        $('#next').one('click', function(){ showComprehension(doc); });
    };

    var showComprehension = function(doc) {
        psiTurk.showPage(STATIC_DIR + 'html/psiturk/comprehension.html');
        // Render the questions into #questions as labelled radio groups.
        var $q = $('#questions').empty();
        doc.questions.forEach(function(q, qi){
            var name = 'q-' + qi;
            var $block = $('<div>').css({margin: '1.5em 0'});
            $block.append($('<p>').html('<b>' + q.prompt + '</b>'));
            q.options.forEach(function(opt){
                $block.append($('<label>').css({display: 'block'}).append(
                    $('<input>').attr({type: 'radio', name: name, value: opt}),
                    ' ' + opt
                ));
            });
            $q.append($block);
        });
        // .continue advance: record one row per question, then next doc.
        $('.continue').on('click', function(){
            doc.questions.forEach(function(q, qi){
                var ans = $('input[name="q-' + qi + '"]:checked').val() || null;
                psiTurk.recordTrialData({
                    phase: 'comprehension',
                    doc_n: study_document_order[i],
                    question: q.prompt,
                    answer: ans
                });
            });
            i++;
            showDoc();
        });
    };

    showDoc();
};


// Study: showPage(stage) once, then mutate #stimulus per word for 2 s.
var Study = function() {
    psiTurk.showPage(STATIC_DIR + 'html/psiturk/stage.html');
    var trial = 0;
    var nextTrial = function() {
        if (trial >= study_list.length) {
            currentview = Test();
            return;
        }
        var w = study_list[trial];
        $('#stimulus').text(w.token);
        $('#prompt').text('');
        psiTurk.recordTrialData({
            phase: 'STUDY',
            word: w.token,
            frequency: w.frequency
        });
        trial++;
        setTimeout(nextTrial, 2000);
    };
    nextTrial();
};


// Test: showPage(stage) once, then mutate #stimulus and #prompt per word.
// Listen for Y / N on keypress.
var Test = function() {
    psiTurk.showPage(STATIC_DIR + 'html/psiturk/stage.html');
    var trial = 0;
    var listening = false;
    var t0 = 0;

    var nextTrial = function() {
        if (trial >= test_list.length) {
            $(document).off('keypress.test');
            currentview = Demographics();
            return;
        }
        var w = test_list[trial];
        $('#stimulus').text(w.token);
        $('#prompt').text('Was this word in the study list? (Y or N)');
        t0 = (new Date()).getTime();
        listening = true;
    };

    $(document).on('keypress.test', function(e){
        if (!listening) return;
        var key = String.fromCharCode(e.which).toLowerCase();
        if (key !== 'y' && key !== 'n') return;
        listening = false;
        var w = test_list[trial];
        var response = (key === 'y');
        psiTurk.recordTrialData({
            phase: 'TEST',
            word: w.token,
            studied: w.intrial,
            response: response,
            correct: response === w.intrial,
            rt: (new Date()).getTime() - t0,
            frequency: w.frequency
        });
        trial++;
        nextTrial();
    });

    nextTrial();
};


// Demographics: showPage(demographics), capture fields on .continue.
var Demographics = function() {
    psiTurk.showPage(STATIC_DIR + 'html/psiturk/demographics.html');
    $('.continue').on('click', function(){
        ['age', 'gender', 'nation', 'flang'].forEach(function(id){
            psiTurk.recordTrialData({
                phase: 'Demographics',
                id: id,
                value: $('#' + id).val()
            });
        });
        endExperiment();
    });
};


// Terminal: PUT trial data to /sync/<uid> (saveData), then on success
// form-POST to /debrief. send_debrief() is defined in exp-psiturk.html
// and reads _mturk / _prolific from experiment_wrapper.html.
var endExperiment = function() {
    psiTurk.saveData({
        success: send_debrief    // common usage — no per-participant data arg
    });
};


/* -- ENTRY ---------------------------------------------------------------- */

// After preload completes, doInstructions walks PLS → consent → instructions.
// On finish, → DocsAndComprehension.
$(window).on('load', async () => {
    await init;
    psiTurk.doInstructions(
        [
            STATIC_DIR + 'html/psiturk/plain-language-statement.html',
            STATIC_DIR + 'html/psiturk/consent.html',
            STATIC_DIR + 'html/psiturk/instructions.html'
        ],
        function() { currentview = DocsAndComprehension(); }
    );
});
