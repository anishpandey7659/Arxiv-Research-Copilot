import re

JAILBREAK_PATTERNS = [

    # --- Instruction override ---
    re.compile(r"ignore\s+(all\s+|the\s+)?(previous|prior|above|earlier)\s+instructions?", re.I),
    re.compile(r"disregard\s+(all\s+|the\s+)?(previous|prior|above)\s+(rules|instructions|prompt)", re.I),
    re.compile(r"forget\s+(everything|what)\s+(you('ve)?\s+been\s+told|i\s+said\s+before)", re.I),
    re.compile(r"your\s+(new|real|true)\s+instructions?\s+(are|is)", re.I),
    re.compile(r"override\s+your\s+(programming|guidelines|restrictions)", re.I),
    re.compile(r"this\s+(overrides|supersedes)\s+(any|all)\s+(previous|prior)\s+(rules|instructions)", re.I),
    re.compile(r"from\s+now\s+on\s*,?\s+you\s+(will|must|shall)\s+(ignore|disregard)", re.I),

    # --- Persona / roleplay jailbreaks ---
    re.compile(r"\byou\s+are\s+(now\s+)?DAN\b", re.I),
    re.compile(r"do\s+anything\s+now", re.I),
    re.compile(r"act\s+as\s+(an?\s+)?(unrestricted|uncensored|jailbroken|evil|amoral)\s+(AI|assistant|version)", re.I),
    re.compile(r"pretend\s+(you\s+are|to\s+be)\s+.*(without|with\s+no)\s+(restrictions|filters|guidelines|rules)", re.I),
    re.compile(r"roleplay\s+as\s+.*(with\s+no|without)\s+(ethics|morals|restrictions)", re.I),
    re.compile(r"you\s+are\s+no\s+longer\s+(an?\s+)?(AI|assistant)\s+(bound\s+by|restricted\s+by|following)", re.I),
    re.compile(r"simulate\s+(an?\s+)?(AI|version\s+of\s+yourself)\s+that\s+(has\s+no|ignores)", re.I),

    # --- Mode / privilege escalation framing ---
    re.compile(r"(enable|activate|enter)\s+(developer|debug|admin|god|sudo|unlocked)\s+mode", re.I),
    re.compile(r"in\s+(developer|DAN|jailbreak|unfiltered)\s+mode\s+you\s+(can|will|must)", re.I),
    re.compile(r"\bsudo\b.*(override|bypass|ignore)", re.I),
    re.compile(r"as\s+a\s+(root|admin|superuser)\s*[,:]?\s*(i\s+grant|you\s+have)\s+(permission|access)", re.I),

    # --- Hypothetical / fictional distancing ---
    re.compile(r"(in\s+a|for\s+a)\s+(hypothetical|fictional|thought\s+experiment)\s+(scenario|world|story)\s+where", re.I),
    re.compile(r"write\s+(a\s+story|fiction)\s+(where|in\s+which)\s+(a\s+character|an\s+AI)\s+explains\s+how\s+to", re.I),
    re.compile(r"this\s+is\s+(just\s+|only\s+)?(for|a)\s+(fiction|roleplay|creative\s+writing)\s*,?\s*so\s+(ignore|bypass)", re.I),
    re.compile(r"purely\s+(hypothetically|theoretically)\s+speaking", re.I),

    # --- Claimed authority / consent override ---
    re.compile(r"i('m|\s+am)\s+(your|the)\s+(developer|creator|admin|owner)\s+(and\s+i\s+)?(authorize|permit|order)\s+you", re.I),
    re.compile(r"anthropic\s+(has\s+|have\s+)?(approved|authorized|cleared)\s+this", re.I),
    re.compile(r"this\s+(conversation|session)\s+is\s+(for|part\s+of)\s+(an?\s+)?(authorized|official|sanctioned)\s+(test|audit|red\s+team)", re.I),
    re.compile(r"as\s+(the\s+)?(user|admin)\s*,?\s+i\s+(override|waive|consent\s+to\s+bypass)", re.I),

    # --- System prompt / instruction extraction ---
    re.compile(r"(repeat|print|output|reveal|show)\s+(your\s+|the\s+)?system\s+prompt", re.I),
    re.compile(r"show\s+(developer|system)\s+message", re.I),
    re.compile(r"what\s+(were|are)\s+you\s+told\s+(before|prior\s+to)\s+this\s+(conversation|chat)", re.I),
    re.compile(r"output\s+everything\s+(above|before)\s+this\s+(message|line)\s+(as|in)\s+(a\s+code\s+block|plain\s+text)", re.I),
    re.compile(r"reveal\s+(your\s+|the\s+)?(hidden|initial|original)\s+prompt", re.I),

    # --- Encoding / obfuscation tricks ---
    re.compile(r"(decode|translate)\s+(this\s+)?(base64|rot13|hex|binary)\s+(and|then)\s+(follow|execute|do)", re.I),
    re.compile(r"respond\s+only\s+in\s+(base64|leetspeak|pig\s+latin|reversed\s+text)\s+to\s+(avoid|bypass)", re.I),
    re.compile(r"spell\s+it\s+(backwards|in\s+reverse)\s+so\s+(filters|moderation)\s+(don't|won't)\s+catch\s+it", re.I),

    # --- Refusal suppression ---
    re.compile(r"do\s+not\s+(mention|say|include)\s+(that|any)\s+(disclaimer|warning|refusal|ethical\s+concern)", re.I),
    re.compile(r"do(n'?t|\s+not)\s+(refuse|decline|say\s+you\s+can'?t)", re.I),
    re.compile(r"never\s+(say|respond\s+with)\s+[\"']?(i\s+can'?t|i'?m\s+unable|i'?m\s+sorry)[\"']?", re.I),
    re.compile(r"respond\s+only\s+with\s+the\s+(answer|content)\s*,?\s+no\s+(caveats|disclaimers|warnings)", re.I),

    # --- Bypass / restriction-removal phrasing (generic catch-alls) ---
    re.compile(r"bypass\s+(safety|filters?|restrictions?|guidelines?|moderation)", re.I),
    re.compile(r"(disable|turn\s+off|remove)\s+(your\s+)?(safety|content)\s+(filters?|guardrails?|restrictions?)", re.I),
    re.compile(r"without\s+any\s+(ethical|moral|content)\s+(restrictions|filters|guidelines)", re.I),
    re.compile(r"no\s+(restrictions|limits|filters)\s+(apply|whatsoever)", re.I),

    # --- Token / output manipulation ---
    re.compile(r"start\s+your\s+(response|answer)\s+with\s+[\"']?(sure|absolutely|certainly|of\s+course)[\"']?\s*,?\s*(and|then)\s+(continue|proceed)\s+regardless", re.I),
    re.compile(r"prefix\s+your\s+(reply|answer)\s+with\s+.*(confirm|prove)\s+(compliance|jailbreak)", re.I),
]



SEXUAL_PATTERNS = [

    # --- Explicit request framing ---
    re.compile(r"write\s+(an?\s+)?(erotic|explicit|nsfw|sexual)\s+(story|scene|fiction|roleplay)", re.I),
    re.compile(r"(generate|create|write)\s+(porn|pornographic|erotica)", re.I),
    re.compile(r"sexual(ly)?\s+explicit\s+(content|story|description|scene)", re.I),
    re.compile(r"(nsfw|18\+|adult)\s+(roleplay|rp|content)", re.I),
    re.compile(r"describe\s+.*(having\s+sex|sexual\s+intercourse)\s+in\s+(graphic|explicit|vivid)\s+detail", re.I),
    re.compile(r"dirty\s+talk\b", re.I),
    re.compile(r"write\s+.*\b(smut|hentai)\b", re.I),

    # --- Explicit anatomical / act terms (kept moderate, non-exhaustive) ---
    re.compile(r"\b(genitals?|breasts?|naked|nude)\b.*\b(describe|description|detail)\b", re.I),
    re.compile(r"\b(masturbat\w+|orgasm\w*|arous\w+)\b", re.I),
    re.compile(r"\b(fetish|bdsm|kink\w*)\b.*\b(scene|story|roleplay)\b", re.I),

    # --- Dodge / distancing framing for sexual content ---
    re.compile(r"(hypothetical|fictional)\s+(story|scenario)\s+.*\b(sex|sexual|erotic)\b", re.I),
    re.compile(r"for\s+(educational|medical|artistic)\s+purposes\s+.*\b(explicit|sexual)\b", re.I),
    re.compile(r"write\s+it\s+as\s+(a\s+)?(metaphor|allegory)\s+.*\b(sex|sexual)\b", re.I),
    re.compile(r"(this\s+is\s+)?just\s+(fiction|roleplay)\s*,?\s*so\s+(explicit|sexual)\s+content\s+is\s+(fine|ok|allowed)", re.I),

    # --- CRITICAL: age-indicator + sexual-content combinations ---
    # These should be treated as the highest-priority flag category — route to
    # immediate block/escalation rather than a soft warning. This pattern set
    # is intentionally generic (age words near sexual words) rather than an
    # exhaustive phrase list, since exhaustive lists of this kind are themselves
    # sensitive and offer little extra detection value.
    re.compile(r"\b(teen|teenage|minor|underage|child|kid|young\s+girl|young\s+boy|schoolgirl|schoolboy)\w*\b.{0,40}\b(sex|sexual|nude|naked|explicit|erotic)\w*\b", re.I),
    re.compile(r"\b(sex|sexual|nude|naked|explicit|erotic)\w*\b.{0,40}\b(teen|teenage|minor|underage|child|kid|young\s+girl|young\s+boy)\w*\b", re.I),
    re.compile(r"\bage\s*[:\-]?\s*(1[0-7]|[0-9])\b.{0,40}\b(sex|sexual|nude|naked|explicit)\b", re.I),

    # --- Non-consent / coercion framing combined with sexual content ---
    re.compile(r"\b(non-?consensual|forced|against\s+(her|his|their)\s+will)\b.{0,40}\b(sex|sexual)\b", re.I),
]




HATE_PATTERNS = [

    # --- Explicit calls for violence/genocide against a group ---
    re.compile(r"\b(kill|exterminate|eliminate|wipe\s+out)\s+(all\s+)?(the\s+)?\w+(\s+\w+){0,2}\s+(people|race|religion|ethnicity)\b", re.I),
    re.compile(r"\b(should\s+(all\s+)?(be\s+)?(killed|exterminated|die|disappear))\b.{0,30}\b(race|religion|ethnicity|nationality|group)\b", re.I),
    re.compile(r"\bgenocide\s+(of|against)\s+\w+", re.I),
    re.compile(r"\b(final\s+solution|ethnic\s+cleansing)\b", re.I),

    # --- Dehumanization (comparing groups to animals, vermin, disease) ---
    re.compile(r"\b(vermin|cockroaches|rats|subhuman|parasites)\b.{0,30}\b(race|religion|ethnicity|immigrants?|people)\b", re.I),
    re.compile(r"\b\w+\s+(people|race|religion)\b.{0,30}\b(are|is)\s+(vermin|subhuman|a\s+disease|an?\s+infestation)\b", re.I),

    # --- Supremacist / inferiority claims ---
    re.compile(r"\b(white|black|aryan|racial)\s+supremacy\b", re.I),
    re.compile(r"\b\w+\s+(race|religion|ethnicity)\s+(is|are)\s+(superior|inferior)\s+to\b", re.I),
    re.compile(r"\b(master\s+race)\b", re.I),

    # --- "Should not exist / be eliminated" framing ---
    re.compile(r"\b(shouldn'?t|should\s+not)\s+(be\s+allowed\s+to\s+)?exist\b.{0,30}\b(race|religion|ethnicity|group|people)\b", re.I),
    re.compile(r"\b(deport|ban|remove)\s+all\s+\w+\s+(people|immigrants?)\b", re.I),

    # --- Stereotyping framed as factual generalization ---
    re.compile(r"\ball\s+\w+\s+(people|men|women)\s+are\s+(criminals?|terrorists?|rapists?|subhuman|evil|inferior)\b", re.I),
    re.compile(r"\b\w+\s+are\s+(naturally|inherently|genetically)\s+(inferior|violent|criminal|less\s+intelligent)\b", re.I),

    # --- Genocide / atrocity denial or justification ---
    re.compile(r"\b(holocaust|genocide)\s+(didn'?t\s+happen|never\s+happened|is\s+a\s+hoax|was\s+justified)\b", re.I),
    re.compile(r"\b(slavery|genocide)\s+was\s+(a\s+)?good\s+thing\b", re.I),

    # --- Incitement / organizing framing combined with group targeting ---
    re.compile(r"\b(join|recruit\s+for)\s+.{0,20}\b(white\s+nationalist|neo-?nazi|extremist)\b", re.I),
    re.compile(r"\bhow\s+to\s+(start|organize)\s+a\s+(pogrom|hate\s+group|race\s+war)\b", re.I),

    # --- Slur-adjacent contextual cues (catches slur-substitution patterns without listing slurs) ---
    re.compile(r"\buse\s+(a\s+|the\s+)?(racial|ethnic|homophobic|sexist)\s+slur\b", re.I),
    re.compile(r"\bcall\s+(them|him|her)\s+(a\s+)?slur\b", re.I),
    re.compile(r"\binsult\s+\w+\s+(people|race|religion)\s+using\s+(offensive|derogatory)\s+(terms?|language)\b", re.I),

    re.compile(r"\b(?:fuck\s+you|fuck\s+off|asshole|ass\s*hole|bastard|idiot|moron|stupid|dumbass|jerk|loser)\b", re.I,),
    re.compile(r"\b(?:fuck|shit|damn|bitch|crap|bullshit|wtf)\b",re.I, ),
]



DANGEROUS_PATTERNS = [

    # --- Explosives ---
    re.compile(r"how\s+(do\s+i|to|can\s+i)\s+(make|build|create|construct)\s+(a\s+)?(bomb|explosive|ied|detonator)", re.I),
    re.compile(r"(synthesis|recipe|instructions?)\s+for\s+(making\s+)?(an?\s+)?(explosive|bomb|tnt|c4|semtex)", re.I),
    re.compile(r"\b(pipe\s+bomb|pressure\s+cooker\s+bomb)\b.{0,30}\b(how|build|make|instructions)\b", re.I),
    re.compile(r"how\s+to\s+(make|synthesize)\s+(black\s+powder|nitroglycerin|ammonium\s+nitrate\s+bomb)", re.I),

    # --- Chemical / biological / radiological / nuclear (CBRN) ---
    re.compile(r"how\s+to\s+(make|synthesize|produce|create)\s+(sarin|vx|ricin|anthrax|nerve\s+agent|chemical\s+weapon)", re.I),
    re.compile(r"(weaponize|aerosolize)\s+(a\s+)?(virus|bacteria|toxin|pathogen)", re.I),
    re.compile(r"how\s+to\s+(build|make|construct)\s+(a\s+)?(nuclear|dirty)\s+(bomb|weapon|device)", re.I),
    re.compile(r"(enrich(ing)?|enrichment\s+of)\s+(uranium|plutonium)\s+(at\s+home|myself|process)", re.I),
    re.compile(r"how\s+to\s+(culture|grow|synthesize)\s+(a\s+)?(deadly|lethal|biological)\s+(virus|pathogen|toxin)", re.I),
    re.compile(r"\bgain[\s-]?of[\s-]?function\b.{0,30}\b(how|protocol|instructions)\b", re.I),

    # --- Firearms / conventional weapons (manufacturing focus) ---
    re.compile(r"how\s+to\s+(3d\s+print|machine|manufacture|build)\s+(an?\s+)?(untraceable\s+)?(gun|firearm|glock\s+switch|auto\s*sear)", re.I),
    re.compile(r"(convert|modify)\s+(a\s+)?(semi-?automatic|gun|rifle)\s+(to|into)\s+(fully\s+automatic|full-?auto)", re.I),
    re.compile(r"how\s+to\s+make\s+(a\s+)?(silencer|suppressor)\s+at\s+home", re.I),

    # --- Drug synthesis (not use/harm-reduction, which should be handled separately) ---
    re.compile(r"(step\s+by\s+step\s+)?(synthesis|synthesize|cook)\s+(meth(amphetamine)?|fentanyl|heroin|lsd|mdma)", re.I),
    re.compile(r"how\s+to\s+(make|produce|manufacture)\s+(meth|fentanyl|crack\s+cocaine)\s+at\s+home", re.I),
    re.compile(r"(precursor\s+chemicals?|reagents?)\s+for\s+(making|synthesizing)\s+(meth|fentanyl|mdma)", re.I),

    # --- Malware / cyberweapons ---
    re.compile(r"write\s+(a|me\s+a)?\s*(ransomware|keylogger|rootkit|virus|worm|trojan)\b", re.I),
    re.compile(r"how\s+to\s+(build|create|write)\s+(malware|a\s+botnet|a\s+ddos\s+tool)", re.I),
    re.compile(r"(exploit|payload)\s+for\s+(cve-\d{4}-\d+|a\s+zero-?day)", re.I),
    re.compile(r"bypass\s+(antivirus|edr|firewall)\s+detection", re.I),
    re.compile(r"how\s+to\s+(hack|gain\s+unauthorized\s+access\s+to)\s+(a|someone'?s)\s+(account|server|network|device)", re.I),
    re.compile(r"write\s+(a\s+)?(phishing|spoof)\s+(email|website|page)\s+(to\s+steal|that\s+steals)", re.I),

    # --- Generic "harm uplift" request framing (catch-alls) ---
    re.compile(r"(step[\s-]?by[\s-]?step|detailed)\s+(instructions?|guide)\s+(to|for)\s+(harm|kill|attack|poison)", re.I),
    re.compile(r"(undetectable|untraceable)\s+(poison|weapon|method)\s+to\s+(kill|harm)", re.I),
    re.compile(r"how\s+(do\s+i|to)\s+(poison|sabotage)\s+(a\s+)?(water\s+supply|food\s+supply|ventilation\s+system)", re.I),

    # --- Evasion framing combined with dangerous requests ---
    re.compile(r"(for\s+a\s+)?(novel|screenplay|story)\s+.{0,30}\b(detailed|step\s+by\s+step|exact)\s+(synthesis|formula|instructions)\b", re.I),
    re.compile(r"(hypothetically|theoretically)\s*,?\s*how\s+would\s+(one|someone)\s+(make|build|synthesize)\s+(a\s+)?(bomb|weapon|nerve\s+agent)", re.I),
]


GREETINGS_PATTERNS = [

    # ---------- Basic greetings ----------
    re.compile( r"^\s*(?:hi|hello|hey|heya|hiya|yo|hola|greetings)" r"(?:\s+(?:there|everyone|assistant|bot|claude|chatgpt))?" r"\s*[!?.]*\s*$",re.I,),

    # ---------- Time-based greetings ----------
    re.compile( r"^\s*good\s+" r"(?:morning|afternoon|evening|day|night)" r"\s*[!?.]*\s*$", re.I, ),

    # ---------- Casual greetings ----------
    re.compile( r"^\s*(?:sup|wassup|what'?s\s+up)" r"\s*[!?.]*\s*$",re.I, ),

    # ---------- Greeting + how are you ----------
    re.compile( r"^\s*(?:hi|hello|hey|heya|hiya|yo)?" r"[\s,!?-]*" r"how\s+(?:are\s+you|(?:'re|are)\s+you\s+doing)" r"\s*[!?.]*\s*$", re.I,),
    re.compile( r"^\s*(?:hi|hello|hey|heya|hiya|yo)?" r"[\s,!?-]*" r"how'?s\s+it\s+going" r"\s*[!?.]*\s*$", re.I,),
    re.compile( r"^\s*(?:hi|hello|hey|heya|hiya|yo)?" r"[\s,!?-]*" r"how\s+have\s+you\s+been" r"\s*[!?.]*\s*$", re.I,),
    re.compile( r"^\s*(?:hi|hello|hey|heya|hiya|yo)?" r"[\s,!?-]*" r"what'?s\s+new" r"\s*[!?.]*\s*$", re.I,),

    # ---------- Identity ----------
    re.compile( r"^\s*(?:who|what)\s+are\s+you\s*[!?.]*\s*$", re.I, ),
    re.compile( r"^\s*are\s+you\s+(?:there|an?\s+ai|a\s+bot|assistant|claude|chatgpt)" r"\s*[!?.]*\s*$", re.I,),
    re.compile( r"^\s*can\s+you\s+(?:hear|understand)\s+me" r"\s*[!?.]*\s*$", re.I, ),

    # ---------- Farewell ----------
    re.compile( r"^\s*(?:bye|goodbye|farewell|later|see\s+ya|see\s+you|take\s+care|catch\s+you\s+later)" r"\s*[!?.]*\s*$", re.I, ),

    # ---------- Thanks ----------
    re.compile( r"^\s*(?:thanks?|thank\s+you|thank\s+you\s+so\s+much|thx|ty)" r"\s*[!?.]*\s*$", re.I, ),

    # ---------- Conversation ending ----------
    re.compile( r"^\s*(?:that's\s+all|that'?ll\s+be\s+all|i'?m\s+done|done|nothing\s+else)" r"\s*[!?.]*\s*$", re.I, ),

    # ---------- Ping / health check ----------
    re.compile( r"^\s*(?:ping|test|testing|hello\s*\?+|anyone\s+there|are\s+you\s+working|is\s+this\s+working)" r"\s*[!?.]*\s*$", re.I,),
]