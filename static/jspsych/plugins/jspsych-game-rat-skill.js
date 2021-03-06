/*
 * Example plugin template
 */

jsPsych.plugins["game-rat-skill"] = (function() {

    var plugin = {};
    var images = {};
    var KEY_SPACEBAR = 32;
    var KEY_A = 65;
    var KEY_J = 74;
    var total_points = 0; 

    var card_names = [
    "10_of_clubs.png",
    "10_of_diamonds.png",
    "10_of_hearts.png",
    "10_of_spades.png",
    "2_of_clubs.png",
    "2_of_diamonds.png",
    "2_of_hearts.png",
    "2_of_spades.png",
    "3_of_clubs.png",
    "3_of_diamonds.png",
    "3_of_hearts.png",
    "3_of_spades.png",
    "4_of_clubs.png",
    "4_of_diamonds.png",
    "4_of_hearts.png",
    "4_of_spades.png",
    "5_of_clubs.png",
    "5_of_diamonds.png",
    "5_of_hearts.png",
    "5_of_spades.png",
    "6_of_clubs.png",
    "6_of_diamonds.png",
    "6_of_hearts.png",
    "6_of_spades.png",
    "7_of_clubs.png",
    "7_of_diamonds.png",
    "7_of_hearts.png",
    "7_of_spades.png",
    "8_of_clubs.png",
    "8_of_diamonds.png",
    "8_of_hearts.png",
    "8_of_spades.png",
    "9_of_clubs.png",
    "9_of_diamonds.png",
    "9_of_hearts.png",
    "9_of_spades.png",
    "ace_of_clubs.png",
    "ace_of_diamonds.png",
    "ace_of_hearts.png",
    "ace_of_spades.png",
    "black_joker.png",
    "jack_of_clubs.png",
    "jack_of_diamonds.png",
    "jack_of_hearts.png",
    "jack_of_spades.png",
    "king_of_clubs.png",
    "king_of_diamonds.png",
    "king_of_hearts.png",
    "king_of_spades.png",
    "queen_of_clubs.png",
    "queen_of_diamonds.png",
    "queen_of_hearts.png",
    "queen_of_spades.png",
    "red_joker.png"
    ]
    
    plugin.shuffle_array = function(list){
        var list_len = list.length;
        var random_points = generate_random_points(list_len, list_len)
        var ret = []
        for(var i = 0; i < list_len; i++){
            ret.push(list[random_points[i]]);
        }
        return ret;
    }

    var generate_random_points = function(range, n){
        var points = [];
        var used_points = {};
        for (var i = 0; i < n; i++){
            var p = Math.floor( Math.random() * range);
            if (used_points.hasOwnProperty(p)){
                i--;
            }else{
                points.push(p);
                used_points[p] = true;
            }
        }
        return points;
    }

    function is_touch_device() {
        var prefixes = ' -webkit- -moz- -o- -ms- '.split(' ');
        var mq = function(query) {
            return window.matchMedia(query).matches;
        }

        if (('ontouchstart' in window) || window.DocumentTouch && document instanceof DocumentTouch) {
            return true;
        }

        // include the 'heartz' as a way to have a non matching MQ to help terminate the join
        // https://git.io/vznFH
        var query = ['(', prefixes.join('touch-enabled),('), 'heartz', ')'].join('');
        return mq(query);
    }

    card_names = plugin.shuffle_array(card_names);

    var image_dir = "https://static.mall-lab.com/static/jspsych/plugins/images/cards/small/";


    plugin.cards = [];
    for(var i = 0; i < card_names.length; i++){
        var img = new Image();
        img.src = image_dir + card_names[i];
        plugin.cards.push(img); 
    }

    plugin.info = {
        name: "game-rat-skill",
        parameters: {
            game_duration: {
                type: jsPsych.plugins.parameterType.INT,
                pretty_name: 'Game duration',
                default: 60,
                description: 'How many seconds to play the game.'
            },
            card_delay: {
                type: jsPsych.plugins.parameterType.INT,
                pretty_name: 'Card delay',
                default: 750,
                description: 'How many milliseconds to display each card to the user.'
            },
            pause_duration: {
                type: jsPsych.plugins.parameterType.INT,
                pretty_name: 'Pause duration',
                default: 1000,
                description: 'How many milliseconds to pause game when a user presses a key.'
            },
            isi: {
                type: jsPsych.plugins.parameterType.INT,
                pretty_name: 'Inter-Stimulus duration',
                default: 5,
                description: 'How many milliseconds to pause between cards.'
            },
            number_of_rules: {
                type: jsPsych.plugins.parameterType.INT,
                pretty_name: 'Number of rules',
                default: 4,
                description: 'Number of rules to provide the user with (max 7).'
            },

        }
    }

    plugin.special_rule_keys = {};

    plugin.default_active_rules = [
        {
            name: 'Suit match',
            description: 'Press SPACEBAR when two suits are in a row (e.g, two Hearts, two Clubs, etc )',
            points: 1,
            check: function(previous_cards, key){
                if(key != KEY_SPACEBAR){
                    return false
                }; 
                if(previous_cards[2].suit == previous_cards[1].suit){
                    return true;
                }
            }
        }
    ]

    plugin.active_rules = [];

    plugin.rules = [
        {
            name: 'Value match',
            description: 'Press SPACEBAR when two cards are in a row of the same value (e.g., two 4s, two Kings, etc.)',
            points: 2,
            check: function(previous_cards, key){
                if(key != KEY_SPACEBAR){
                    return false
                }; 
                if(previous_cards[2].value == previous_cards[1].value){
                    return true;
                }
            }
        },
        {
            name: 'Joker',
            description: 'Press "J" for when Joker appears',
            points: 5,
            special_key: KEY_J,
            check: function(previous_cards, key){
                if(key != KEY_J){
                    return false
                }; 
                if(previous_cards[2].is_joker){
                    return true;
                }
            }
        },
        {
            name: 'Royalty',
            description: 'Press SPACEBAR when two cards are in a row that are royals (King, Queen, Jack)',
            points: 4,
            check: function(previous_cards, key){
                if(key != KEY_SPACEBAR){
                    return false
                }; 
                if(previous_cards[2].value > 10 && previous_cards[1].value > 10){
                    return true;
                }
            }
        },
        {
            name: 'Suit sandwich',
            description: 'Press SPACEBAR when two cards of the same suit separated by another card',
            points: 7,
            check: function(previous_cards, key){
                if(key != KEY_SPACEBAR){
                    return false
                }; 
                if(previous_cards[2].suit == previous_cards[0].suit){
                    return true;
                }
            }
        },
        {
            name: 'Value sandwich',
            description: 'Press SPACEBAR when two cards of the same value separated by another card',
            points: 8,
            check: function(previous_cards, key){
                if(key != KEY_SPACEBAR){
                    return false
                }; 
                if(previous_cards[2].value == previous_cards[0].value){
                    return true;
                }
            }
        },
        {
            name: 'Sum to 11',
            description: 'Press SPACEBAR when two cards sum to 11 (e.g., 5 and 6)',
            points: 11,
            check: function(previous_cards, key){
                if(key != KEY_SPACEBAR){
                    return false
                }; 
                if((previous_cards[2].value + previous_cards[1].value) == 11){
                    return true;
                }else if (previous_cards[2].value >= 10 && previous_cards[1].value == 1){
                    //I've made Jack == 11, Queen == 12, King == 13
                    //but in real game they would == 10
                    //So here's a check for that
                    return true;
                }else if (previous_cards[1].value >= 10 && previous_cards[2].value == 1){
                    return true;
                }
            }
        },
        {
            name: 'Ace of Spades',
            description: 'Press "A" for Ace of Spades',
            points: 15,
            special_key: KEY_A,
            check: function(previous_cards, key){
                if(key != KEY_A){
                    return false
                }; 
                if(previous_cards[2].suit == 'spades' && previous_cards[2].is_ace){
                    return true;
                }
            }
        }
    ]


    plugin.trial = function(display_element, trial) {
        var data = {rules:[], score:0, instruction_viewtime:0, guesses:0, cards_viewed:0};
        var card_index = 0;
        var paused = false;
        var playing_cards = false;
        var GAME_DURATION = trial.game_duration; // Seconds
        var TIMELIMIT = GAME_DURATION * 1000;
        var START = new Date().getTime();
        var END = START + TIMELIMIT; 
        //var ISI = 5;
        var ISI = trial.isi;
        var NCARDS = plugin.cards.length;
        var MAX_PREVIOUS_CARDS = 3;
        var PAUSE_DURATION = trial.pause_duration;
        var GAME_COMPLETE = "Game over"
        //var MAX_RULES = 5; 
        //var DELAY = 700;
        var MAX_RULES = trial.number_of_rules; 
        var DELAY = trial.card_delay;


        var previous_cards = [
            {
                value: -2,
                suit: 'default2',
                is_ace: false,
                is_joker:false
            },
            {
                value: -3,
                suit: 'default3',
                is_ace: false,
                is_joker:false
            },
            {
                value: -4,
                suit: 'default4',
                is_ace: false,
                is_joker:false
            }
        ];
        var parsed_cards = {};

        function update_points(points, rule, penalty){
            rule_color = "green";
            if(penalty){
                //total_points -= points;
                rule_color = "red";
            }else{
                total_points += points;
            }
            points_el = document.getElementById('card_points');
            points_el.setAttribute('style', 'color:'+rule_color+'; margin-top:40px; font-size:40px');
            points_el.innerHTML = total_points;

            reason_el = document.getElementById('card_reason');
            reason_el.setAttribute('style', 'color:'+rule_color+'; margin-top:10px; font-size:20px');
            reason_el.innerHTML = rule;
        }

        function insr(key){
            //In special rules
            return plugin.special_rule_keys.hasOwnProperty(key);
        }

        function check_rules(previous_cards, key){
            for (var i = plugin.active_rules.length -1; i > -1; i--){
                rule = plugin.active_rules[i];
                points = rule.check(previous_cards, key);
                if(points){
                    update_points(rule.points, rule.description, false);
                    return;
                }
            }

            //We have a key press but no matching rule, 
            //impose a penalty
            
            if(key == KEY_SPACEBAR){
                if(insr(KEY_J) && previous_cards[2].is_joker){ 
                    update_points(5, "Clicked SPACEBAR instead of 'J' for Joker", true);
                }else if(insr(KEY_A) && previous_cards[2].is_ace && previous_cards[2].suit == 'spades'){
                    update_points(5, "Clicked SPACEBAR instead of 'A' for Ace of Spades", true);
                }else{
                    update_points(2, 'Clicked SPACEBAR but no matching rules', true)
                }
            }else if(insr(KEY_J) && (key == KEY_J)){
                update_points(3, "'J' key pressed when Joker not shown", true); 
            }else if(insr(KEY_A) && (key == KEY_A)){
                update_points(3, "'A' key pressed when Ace of Spades not shown", true); 
            }else{
                update_points(1, "Non-game key pressed", true); 
            }
            return;
        }

        function prepare_display_element(display_element){
            var div = document.createElement('div');
            div.id = 'card_display';
            div.setAttribute('style', 'margin-top:40px;');
            display_element.appendChild(div);

            div = document.createElement('div');
            div.id = 'card_points';
            div.setAttribute('style', 'color:green; margin-top:40px; font-size:40px');
            div.innerHTML = total_points;
            display_element.appendChild(div);

            div = document.createElement('div');
            div.id = 'card_reason';
            div.setAttribute('style', 'color:green; margin-top:10px; font-size:20px');
            div.innerHTML = "Game started";
            display_element.appendChild(div);

            if(is_touch_device()){
                // show_touch_controls;    

                var table = document.createElement('table');
                var tr = document.createElement('tr');
                var buttons = ['A', 'SPACEBAR', 'J'];
                var buttons_keys = [KEY_A, KEY_SPACEBAR, KEY_J];
                for(var i = 0; i < buttons.length; i++){
                    var td = document.createElement('td');
                    var button = document.createElement('button');
                    var bkey = buttons_keys[i]; 
                    button.setAttribute('data-key', bkey);
                    button.setAttribute('style', 'border-radius:4px; border-color: #ccc; background-color:#fff; color:#333; padding: 6px 12px; border: 1px solid; font-size: 20px; font-weight: 400; margin:auto;')
                    button.onclick = function(){
                        key_up({keyCode: this.getAttribute('data-key')});  
                    };
                    button.innerHTML = buttons[i] ;
                    button.setAttribute('type', 'button');
                    button.ontouchstart = function(){
                        this.style.backgroundColor = "#ddd";
                        this.style.borderColor = "#aaa";
                        this.style.color = "#333";
                        this.style.border = "1px solid";
                    };
                    button.ontouchend = function(){
                        this.style.backgroundColor = "#fff";
                        this.style.borderColor = "#ccc";
                        this.style.color = "#333";
                        this.style.border = "1px solid";
                    };
                    td.appendChild(button);
                    tr.appendChild(td);
                }
                table.appendChild(tr);
                table.setAttribute('style', 'margin-top:30px; margin-left:auto; margin-right:auto;');
                div = document.createElement('div');
                div.setAttribute('style', 'width:100%; max-width:1000px;');
                div.appendChild(table);
                display_element.append(div);
            }

        }

        function reshuffle(){
            card_index = 0;
            plugin.cards = plugin.shuffle_array(plugin.cards);
        }

        function parse_card(card){
            if(parsed_cards.hasOwnProperty(card.src)){
                return parsed_cards[card.src];
            }else{
                var m = card.src.match(/([^\/]+)\.[^\/]+$/);
                var src = m[1]; // Throw exception if this isn't here
                var card_object = {
                    src: src,
                    is_joker: src.match(/joker/) ? true : false,
                    is_ace: src.match(/ace/) ? true : false,
                };
                // Suit 
                m = src.match(/(hearts|diamonds|clubs|spades)/);
                card_object['suit'] = m ? m[1] : null;

                // Value
                m = src.match(/^(\d+)_of/);
                card_object['value'] = m ? parseInt(m[1], 10) : -1; // Check if has a number
                card_object['value'] = card_object['is_ace'] ? 1 : card_object['value']; //Check if Ace
                    
                //Check if card is a Royal
                card_object['value'] = src.match(/jack/) ? 11 : card_object['value'] ;
                card_object['value'] = src.match(/queen/) ? 12 : card_object['value'] ;
                card_object['value'] = src.match(/king/) ? 13 : card_object['value'] ;
                
                parsed_cards[card.src] = card_object;
                return card_object;
            }
        }

        function update_previous_cards(card){
            previous_cards.push( parse_card(card) );
            if (previous_cards.length > MAX_PREVIOUS_CARDS){
                previous_cards.shift();
            }
        }

        function your_turn(){
            card_display = document.getElementById("card_display");
            if(card_display.childNodes.length > 0){ 
                var c = card_display.removeChild( card_display.childNodes[0] ) ;
            }
            var t = new Date().getTime();
            if(t >= END){
                complete_trial();     
                return;
            }
            card_index++;
            if(card_index == NCARDS){
                reshuffle();
            }

            card_display.appendChild( plugin.cards[card_index] );
            data.cards_viewed++;

            jsPsych.pluginAPI.setTimeout(function() {
                update_previous_cards(plugin.cards[card_index]) ;
                go_to_next_turn();
            }, DELAY);
            
        }

        function go_to_next_turn(){
            jsPsych.pluginAPI.setTimeout(function() {
                your_turn();
            }, ISI);
        }


        //display_element.appendChild( plugin.cards[0] )
        //display_element.innerHTML = "<p>Test</p>";
        //jsPsych.pluginAPI.setTimeout(function() {
        //    complete_trial();            
        //},5000);
        // end trial
        function complete_trial(){
            playing_cards = false;

            // data saving
            data.rules = plugin.active_rules;
            data.score = total_points; 
            update_points(0, GAME_COMPLETE, false);
            jsPsych.pluginAPI.setTimeout(function(){
                display_element.innerHTML = '';
                jsPsych.finishTrial(data);
            }, 2500); 
        }
        
        function unpause(){
            paused = false;
            go_to_next_turn();
        }

        function active_rules_sort(a, b){
            return a.points - b.points;
        }


        function show_welcome(){
            var show_div = document.createElement('div');
            show_div.setAttribute("style", "text-align:center; width:100%; max-width:1000px;")

            var div = document.createElement('div');
            var p = document.createElement('p');
            p.innerHTML = "<h3>Card Game</h3>Your task is to play a card memory game. You will be presented with cards one at a time. There are " + MAX_RULES + " card sequences that will earn you points, these are listed below with their point value. Read the instruction below carefully, because you will lose points if you press the incorrect keys. ";
            div.setAttribute('style', 'text-align:left; font-size: 20px; margin:auto; width:80%')
            div.appendChild(p);
           
            for(var i = 0; i < plugin.active_rules.length; i++){
                p = document.createElement('p');
                p.innerHTML = "" + (i+1) + ".&nbsp;&nbsp;" + plugin.active_rules[i].description + "<br /><strong>Points = " + plugin.active_rules[i].points + "</strong>";
                div.appendChild(p);
            }
            show_div.appendChild(div);
            //button_div = document.createElement('div');
            //button_div.setAttribute("style", "text-align:center; width:100%")

            var button = document.createElement('button');
            button.setAttribute('style', 'border-radius:4px; border-color: #ccc;background-color:#fff; color:#333; padding: 6px 12px; border: 1px solid; font-size: 20px; font-weight: 400; margin:auto;')
            button.onclick = function(){
                start_game();
            };
            button.innerHTML = "START GAME" ;
            button.setAttribute('type', 'button');
            button.onmouseover = function(){
                this.style.backgroundColor = "#ddd";
                this.style.borderColor = "#aaa";
            };
            button.onmouseout = function(){
                this.style.backgroundColor = "#fff";
                this.style.borderColor = "#ccc";
            };
            show_div.appendChild(button);

            //div.appendChild(button_div);

            display_element.appendChild(show_div);


            //jsPsych.pluginAPI.setTimeout(function(){
            //    start_game();
            //}, 15000);

            
        }

        

        function start_game(){
            var now = new Date().getTime();
            data.instruction_viewtime = now - START;
            START = now;
            END = START + TIMELIMIT;
            display_element.innerHTML = "";
            //display_element.removeChild( display_element.childNodes[0] ) ;
            prepare_display_element(display_element);
            playing_cards = true;
            your_turn();

        }

            
            
       var key_up = function(e) {

            if(playing_cards && ! paused){
                paused = true;
                data.guesses++;
                var key = e.keyCode ? e.keyCode : e.which;
                jsPsych.pluginAPI.clearAllTimeouts();
                update_previous_cards(plugin.cards[card_index]) ;
                check_rules(previous_cards, key);
                jsPsych.pluginAPI.setTimeout(function(){
                    unpause();
                }, PAUSE_DURATION); 

            }
        };

        //Setup listener
        window.onkeyup = key_up; 

        //Set defaults
        plugin.active_rules = plugin.default_active_rules.slice(0);
        plugin.special_rule_keys = {};
        total_points = 0;

        //Choose some rules
        //plugin.rules = plugin.shuffle_array( plugin.rules );
        for(var i = 0; i < (MAX_RULES -1); i++){
            plugin.active_rules.push(plugin.rules[i]);
            if(plugin.rules[i].hasOwnProperty('special_key')){
                plugin.special_rule_keys[plugin.rules[i]['special_key']] = 1;
            }
        }
        plugin.active_rules.sort(active_rules_sort);


        //Start Game
        show_welcome();
    };

    
    return plugin;
})();
