/**
 * Curiosity Cat — Adventure Slider
 * Vanilla JS, no dependencies. Handles skins, unlock tiers, persistence, RTL.
 */

(function () {
  'use strict';

  // ── SKIN CONTENT ──────────────────────────────────────────────────────────

  var SKINS = {
    cat: {
      en: {
        labels: ['Housecat', 'Alley Cat', 'Tiger'],
        descs: [
          'Stay close to home. Standing orders enforced. Nothing leaves the yard.',
          'Calculated risks accepted. Braver exploration. Still comes home.',
          'Widest range. Explores the edge. Reports back – rare places and tales of danger.'
        ]
      },
      ar: {
        labels: ['قط المنزل', 'قط الشوارع', 'النمر'],
        descs: [
          'البقاء قريباً من المنزل. الأوامر الثابتة مُنفَّذة. لا شيء يغادر الساحة.',
          'مخاطر محسوبة مقبولة. استكشاف أكثر جرأة. ولا يزال يعود إلى المنزل.',
          'أوسع نطاق. يستكشف الحدود. يُقدِّم تقاريره — أماكن نادرة وحكايات من الخطر.'
        ]
      },
      zh: {
        labels: ['家猫', '街猫', '猛虎'],
        descs: [
          '紧守家门。严格执行常规指令。没有任何东西能离开院子。',
          '接受有计算的风险。更大胆的探索。仍然安全回家。',
          '活动范围最广。探索边界。带回报告——罕见之地与险境故事。'
        ]
      },
      hi: {
        labels: ['घरेलू बिल्ली', 'गली की बिल्ली', 'बाघ'],
        descs: [
          'घर के पास रहें। स्थायी आदेश लागू। कुछ भी आंगन नहीं छोड़ता।',
          'गणनाबद्ध जोखिम स्वीकृत। अधिक साहसी अन्वेषण। फिर भी घर लौटता है।',
          'सबसे विस्तृत सीमा। किनारे की खोज करता है। वापस रिपोर्ट करता है — दुर्लभ स्थान और खतरे की कहानियां।'
        ]
      },
      ta: {
        labels: ['வீட்டுப் பூனை', 'தெரு பூனை', 'புலி'],
        descs: [
          'வீட்டிற்கு அருகில் இருங்கள். நிரந்தர உத்தரவுகள் செயல்படுத்தப்படுகின்றன. எதுவும் முற்றத்தை விட்டு வெளியேறாது.',
          'கணக்கிடப்பட்ட அபாயங்கள் ஏற்றுக்கொள்ளப்படுகின்றன. தைரியமான ஆய்வு. இன்னும் வீடு திரும்புகிறது.',
          'மிகப் பரந்த வரம்பு. விளிம்பை ஆராய்கிறது. திரும்ப அறிக்கை அளிக்கிறது — அரிய இடங்கள் மற்றும் ஆபத்தின் கதைகள்.'
        ]
      }
    },
    rat: {
      en: {
        labels: ['Lab Rat', 'Street Rat', 'King Rat'],
        descs: [
          'Controlled conditions. Every run mapped. Nothing unexpected.',
          'Out in the world. Smart about the route. Avoids the traps.',
          'First through the tunnel. Finds what the others missed.'
        ]
      },
      ar: {
        labels: ['فأر المختبر', 'فأر الشارع', 'ملك الفئران'],
        descs: [
          'ظروف خاضعة للسيطرة. كل مسار مُرسَم. لا شيء غير متوقع.',
          'في العالم الخارجي. ذكي في اختيار المسار. يتجنب الفخاخ.',
          'الأول عبر النفق. يعثر على ما فاته الآخرون.'
        ]
      },
      zh: {
        labels: ['实验鼠', '街头鼠', '鼠王'],
        descs: [
          '受控条件。每条路径已绘制。没有意外。',
          '走出去闯世界。路线选择聪明。避开陷阱。',
          '第一个穿越隧道。发现其他人错过的东西。'
        ]
      },
      hi: {
        labels: ['लैब चूहा', 'स्ट्रीट रैट', 'किंग रैट'],
        descs: [
          'नियंत्रित स्थितियां। हर रन मैप किया गया। कुछ भी अप्रत्याशित नहीं।',
          'दुनिया में बाहर। रास्ते के बारे में होशियार। जाल से बचता है।',
          'सुरंग के पार पहला। जो दूसरों ने चूका वो ढूंढ लेता है।'
        ]
      },
      ta: {
        labels: ['ஆய்வக எலி', 'தெரு எலி', 'மன்னன் எலி'],
        descs: [
          'கட்டுப்பாட்டு நிலைமைகள். ஒவ்வொரு ஓட்டமும் வரைபடமிடப்பட்டது. எதுவும் எதிர்பாராதது இல்லை.',
          'உலகில் வெளியே. பாதை பற்றி புத்திசாலித்தனமானது. கண்ணிகளை தவிர்க்கிறது.',
          'சுரங்கத்தின் வழியே முதல். மற்றவர்கள் தவறவிட்டதை கண்டுபிடிக்கிறது.'
        ]
      }
    },
    puppy: {
      en: {
        labels: ['Puppy', 'Yard Dog', 'Wolf'],
        descs: [
          'On the leash. Close to home. Trained behaviours only.',
          'Off the leash in the yard. Curious. Comes when called.',
          'Wide-ranging. Hunts alone. Reports back.'
        ]
      },
      ar: {
        labels: ['جرو', 'كلب الحديقة', 'ذئب'],
        descs: [
          'على الرباط. قريب من المنزل. سلوكيات مُدرَّبة فحسب.',
          'طليق في الحديقة. فضولي. يستجيب حين يُنادى.',
          'نطاق واسع. يصطاد بمفرده. يُقدِّم التقارير.'
        ]
      },
      zh: {
        labels: ['小狗', '院犬', '狼'],
        descs: [
          '拴着绳子。靠近家。只有训练行为。',
          '在院子里解开绳子。好奇。一叫就来。',
          '活动范围广。独自狩猎。带回报告。'
        ]
      },
      hi: {
        labels: ['पिल्ला', 'आंगन का कुत्ता', 'भेड़िया'],
        descs: [
          'पट्टे पर। घर के पास। केवल प्रशिक्षित व्यवहार।',
          'आंगन में पट्टे से मुक्त। जिज्ञासु। बुलाने पर आता है।',
          'विस्तृत सीमा। अकेले शिकार करता है। वापस रिपोर्ट करता है।'
        ]
      },
      ta: {
        labels: ['குட்டிநாய்', 'முற்றத்து நாய்', 'ஓநாய்'],
        descs: [
          'கட்டப்பட்டுள்ளது. வீட்டிற்கு அருகில். பயிற்சி பெற்ற நடத்தைகள் மட்டுமே.',
          'முற்றத்தில் விடுவிக்கப்பட்டது. ஆர்வமுள்ளது. அழைக்கும்போது வருகிறது.',
          'பரந்த வரம்பு. தனியாக வேட்டையாடுகிறது. திரும்ப அறிக்கை அளிக்கிறது.'
        ]
      }
    },
    camel: {
      en: {
        labels: ['Pet Camel', 'Trail Camel', 'Dune Racer'],
        descs: [
          'Stabled. Fed by hand. Knows the paddock.',
          'On the caravan route. Calculated trips. Returns to water.',
          'Off the route. Beyond the last well. Brings back the map.'
        ]
      },
      ar: {
        labels: ['جمل الحديقة', 'جمل القافلة', 'سابق الكثبان'],
        descs: [
          'في الإسطبل. يُطعَم يدوياً. يعرف الحظيرة.',
          'على درب القافلة. رحلات محسوبة. يعود إلى الماء.',
          'خارج الدرب. ما وراء البئر الأخيرة. يعود بالخريطة.'
        ]
      },
      zh: {
        labels: ['宠物骆驼', '驼道骆驼', '沙丘赛者'],
        descs: [
          '圈养。手饲。熟悉围场。',
          '走商队路线。有计划的旅途。返回水源。',
          '偏离路线。越过最后一口井。带回地图。'
        ]
      },
      hi: {
        labels: ['पालतू ऊंट', 'रास्ते का ऊंट', 'टीला दौड़ाक'],
        descs: [
          'अस्तबल में। हाथ से खिलाया गया। चरागाह जानता है।',
          'कारवां मार्ग पर। गणनाबद्ध यात्राएं। पानी पर लौटता है।',
          'मार्ग से बाहर। आखिरी कुएं से परे। नक्शा वापस लाता है।'
        ]
      },
      ta: {
        labels: ['செல்லப் பிராணி ஒட்டகம்', 'பாதை ஒட்டகம்', 'மணல்மேடு ஓட்டக்காரன்'],
        descs: [
          'தொழுவத்தில். கையால் உணவளிக்கப்படுகிறது. மேய்ச்சல் நிலம் தெரியும்.',
          'கேரவான் பாதையில். கணக்கிடப்பட்ட பயணங்கள். நீரிடம் திரும்புகிறது.',
          'பாதையை விட்டு வெளியே. கடைசி கிணற்றுக்கு அப்பால். வரைபடம் திரும்பக் கொண்டுவருகிறது.'
        ]
      }
    },
    panda: {
      en: {
        labels: ['Baby Panda', 'Forest Panda', 'Wild Panda'],
        descs: [
          'Close to the enclosure. Watched at every step.',
          'In the reserve. Wider territory. Still monitored.',
          'Mountain range. Own decisions. Rare sightings.'
        ]
      },
      ar: {
        labels: ['بنده الصغير', 'بنده الغابة', 'البنده البري'],
        descs: [
          'قريب من الحظيرة. مُراقَب في كل خطوة.',
          'في المحمية. نطاق أوسع. لا يزال تحت المراقبة.',
          'سلسلة الجبال. قراراته الخاصة. مشاهدات نادرة.'
        ]
      },
      zh: {
        labels: ['熊猫宝宝', '林中熊猫', '野生熊猫'],
        descs: [
          '靠近围栏。每一步都被看守。',
          '在保护区里。领地更广。仍受监控。',
          '山脉之中。自己做决定。难得一见。'
        ]
      },
      hi: {
        labels: ['बेबी पांडा', 'वन पांडा', 'जंगली पांडा'],
        descs: [
          'बाड़े के पास। हर कदम पर देखा जाता है।',
          'रिजर्व में। व्यापक क्षेत्र। अभी भी निगरानी में।',
          'पर्वत श्रृंखला। अपने निर्णय। दुर्लभ दर्शन।'
        ]
      },
      ta: {
        labels: ['குட்டி பாண்டா', 'காட்டு பாண்டா', 'காட்டுப் பாண்டா'],
        descs: [
          'கூண்டிற்கு அருகில். ஒவ்வொரு அடியிலும் கவனிக்கப்படுகிறது.',
          'காப்பகத்தில். பரந்த பகுதி. இன்னும் கண்காணிக்கப்படுகிறது.',
          'மலைத் தொடர். சொந்த முடிவுகள். அரிதான தரிசனங்கள்.'
        ]
      }
    },
    primate: {
      en: {
        labels: ['Marmoset', 'Macaque', 'Gorilla'],
        descs: [
          'Treetops only. Small territory. Predictable.',
          'Streets and temples. Takes what\'s offered. Street-smart.',
          'Deep forest. Sets its own path. What it finds, no one else does.'
        ]
      },
      ar: {
        labels: ['مارموزيت', 'قرد الماكاك', 'غوريلا'],
        descs: [
          'قمم الأشجار فحسب. نطاق صغير. متوقع.',
          'الشوارع والمعابد. يأخذ ما يُعرَض. ذكي في الشارع.',
          'أعماق الغابة. يرسم مساره الخاص. ما يعثر عليه لا يجده أحد غيره.'
        ]
      },
      zh: {
        labels: ['狨猴', '猕猴', '大猩猩'],
        descs: [
          '只在树梢。领地小。行为可预测。',
          '街道与寺庙。有什么就拿什么。街头智慧。',
          '深林之中。走自己的路。它的发现，别人没有。'
        ]
      },
      hi: {
        labels: ['मार्मोसेट', 'मकाक', 'गोरिल्ला'],
        descs: [
          'केवल पेड़ों की चोटी। छोटा क्षेत्र। अनुमानित।',
          'सड़कें और मंदिर। जो मिले ले लेता है। स्ट्रीट-स्मार्ट।',
          'गहरा जंगल। अपना रास्ता बनाता है। जो यह पाता है, कोई और नहीं पाता।'
        ]
      },
      ta: {
        labels: ['மார்மோசெட்', 'மக்காக்', 'கொரில்லா'],
        descs: [
          'மரத்தின் உச்சியில் மட்டும். சிறிய பகுதி. கணிக்கக்கூடியது.',
          'தெருக்கள் மற்றும் கோவில்கள். கிடைப்பதை எடுத்துக்கொள்கிறது. தெரு புத்திசாலி.',
          'ஆழமான காடு. சொந்த பாதை அமைக்கிறது. அது கண்டுபிடிப்பதை வேறு யாரும் கண்டுபிடிப்பதில்லை.'
        ]
      }
    },
    cobra: {
      en: {
        labels: ['Garden Cobra', 'Forest Cobra', 'King Cobra'],
        descs: [
          'Familiar ground. Coiled. Warning first.',
          'Further out. Rising. Tracks what moves.',
          'Apex. Strikes when it chooses. Brings back what it learns.'
        ]
      },
      ar: {
        labels: ['كوبرا الحديقة', 'كوبرا الغابة', 'كوبرا الملك'],
        descs: [
          'أرض مألوفة. مُلتَفَّة. التحذير أولاً.',
          'أبعد مدى. يرتفع. يتتبع كل ما يتحرك.',
          'القمة. يضرب حين يختار. يعود بما تعلَّمه.'
        ]
      },
      zh: {
        labels: ['花园眼镜蛇', '森林眼镜蛇', '眼镜王蛇'],
        descs: [
          '熟悉的领地。盘绕待命。先发警告。',
          '更远的地方。昂首而立。追踪一切移动。',
          '顶端。择机出击。带回所学。'
        ]
      },
      hi: {
        labels: ['बगीचे का कोबरा', 'वन कोबरा', 'किंग कोबरा'],
        descs: [
          'परिचित भूमि। कुंडली। पहले चेतावनी।',
          'और आगे। उठता है। जो हिलता है उसे ट्रैक करता है।',
          'शीर्ष। जब चाहे वार करता है। जो सीखता है वापस लाता है।'
        ]
      },
      ta: {
        labels: ['தோட்ட நாகம்', 'காட்டு நாகம்', 'ராஜ நாகம்'],
        descs: [
          'பரிச்சயமான நிலம். சுருண்டு கிடக்கிறது. முதலில் எச்சரிக்கை.',
          'மேலும் தொலைவில். எழுகிறது. நகர்வதை கண்காணிக்கிறது.',
          'உச்சியில். தேர்ந்தெடுக்கும்போது தாக்குகிறது. கற்றதை திரும்பக் கொண்டுவருகிறது.'
        ]
      }
    }
  };

  // ── LANGUAGE → ANIMAL MAPPING ─────────────────────────────────────────────

  var LANG_ANIMALS = {
    en: { default: 'cat', tier1: 'rat', tier2: ['puppy', 'panda'] },
    ar: { default: 'cat', tier1: 'rat', tier2: 'camel' },
    zh: { default: 'cat', tier1: 'rat', tier2: 'panda' },
    hi: { default: 'cat', tier1: 'rat', tier2: 'cobra' },
    ta: { default: 'cat', tier1: 'rat', tier2: 'primate' }
  };

  var SKIN_EMOJIS = {
    cat: '🐱', rat: '🐀', puppy: '🐶',
    camel: '🐪', panda: '🐼', primate: '🐒', cobra: '🐍'
  };

  // ── TOAST MESSAGES ────────────────────────────────────────────────────────

  var TOASTS = {
    en: {
      tier1: '🐀 Street Rat skin unlocked — try it!',
      tier2: function (emoji, name) { return emoji + ' ' + name + ' unlocked — explore further!'; }
    },
    ar: {
      tier1: '🐀 جلد فأر الشارع مفتوح — جرّبه!',
      tier2: function (emoji, name) { return emoji + ' ' + name + ' مفتوح!'; }
    },
    zh: {
      tier1: '🐀 街头鼠皮肤已解锁——试试看！',
      tier2: function (emoji, name) { return emoji + ' ' + name + '已解锁！'; }
    },
    hi: {
      tier1: '🐀 स्ट्रीट रैट स्किन अनलॉक — आज़माएं!',
      tier2: function (emoji, name) { return emoji + ' ' + name + ' अनलॉक!'; }
    },
    ta: {
      tier1: '🐀 ஸ்ட்ரீட் ரேட் ஸ்கின் திறக்கப்பட்டது — முயற்சிக்கவும்!',
      tier2: function (emoji, name) { return emoji + ' ' + name + ' திறக்கப்பட்டது!'; }
    }
  };

  // Skin display names per language (for toast tier2)
  var SKIN_NAMES = {
    puppy: { en: 'Puppy', ar: 'الجرو', zh: '小狗', hi: 'पिल्ला', ta: 'குட்டிநாய்' },
    panda: { en: 'Panda', ar: 'البنده', zh: '熊猫', hi: 'पांडा', ta: 'பாண்டா' },
    camel: { en: 'Camel', ar: 'الجمل', zh: '骆驼', hi: 'ऊंट', ta: 'ஒட்டகம்' },
    cobra: { en: 'Cobra', ar: 'الكوبرا', zh: '眼镜蛇', hi: 'कोबरा', ta: 'நாகம்' },
    primate: { en: 'Primate', ar: 'الرئيسيات', zh: '灵长类', hi: 'प्राइमेट', ta: 'பிரைமேட்' }
  };

  // ── TOAST ELEMENT ─────────────────────────────────────────────────────────

  var toastEl = null;
  var toastTimer = null;

  function getToast() {
    if (!toastEl) {
      toastEl = document.createElement('div');
      toastEl.className = 'skin-unlock-toast';
      document.body.appendChild(toastEl);
    }
    return toastEl;
  }

  function showToast(msg) {
    var el = getToast();
    el.textContent = msg;
    el.classList.add('visible');
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      el.classList.remove('visible');
    }, 3500);
  }

  // ── PER-SLIDER STATE ──────────────────────────────────────────────────────

  function initSlider(wrapper) {
    var lang = wrapper.getAttribute('data-lang') || 'en';
    var isRTL = (lang === 'ar') || (document.documentElement.dir === 'rtl');
    var langMap = LANG_ANIMALS[lang] || LANG_ANIMALS.en;

    // Resolve stored or default state
    var storedPos = parseInt(localStorage.getItem('cc-adventure-level') || '0', 10);
    var storedSkin = localStorage.getItem('cc-skin') || langMap.default;
    var storedTier = parseInt(localStorage.getItem('cc-unlocked-tier') || '0', 10);

    var pos = (storedPos >= 0 && storedPos <= 2) ? storedPos : 0;
    var activeSkin = storedSkin;
    var unlockedTier = storedTier;

    // Verify skin is actually available for current tier
    var availableSkins = getAvailableSkins(lang, unlockedTier);
    if (availableSkins.indexOf(activeSkin) === -1) {
      activeSkin = langMap.default;
    }

    // Inject .slider-video div (before skin-picker, before track-wrapper)
    var videoDiv = document.createElement('div');
    videoDiv.className = 'slider-video';
    wrapper.insertBefore(videoDiv, wrapper.firstChild);

    // Inject .skin-picker div (after video, before track-wrapper)
    var skinPicker = document.createElement('div');
    skinPicker.className = 'skin-picker';
    wrapper.insertBefore(skinPicker, videoDiv.nextSibling);

    // Refs to existing elements
    var handle = wrapper.querySelector('.slider-handle');
    var labelEls = wrapper.querySelectorAll('.slider-label');
    var descEl = wrapper.querySelector('.slider-desc');
    var skinNameEl = wrapper.querySelector('.slider-skin-name');

    // ── RENDER ───────────────────────────────────────────────────────────────

    function render() {
      var skinData = getSkinData(activeSkin, lang);
      var labels = skinData.labels;
      var descs = skinData.descs;

      // Update labels
      for (var i = 0; i < labelEls.length; i++) {
        labelEls[i].textContent = labels[i] || '';
      }

      // Update desc
      if (descEl) descEl.textContent = descs[pos] || '';

      // Update skin name
      if (skinNameEl) {
        var skinLabel = labels[pos];
        skinNameEl.textContent = skinLabel ? (SKIN_EMOJIS[activeSkin] || '') + ' ' + skinLabel : '';
      }

      // Position handle
      var pct = pos === 0 ? '0%' : pos === 1 ? '50%' : '100%';
      if (isRTL) {
        pct = pos === 0 ? '100%' : pos === 1 ? '50%' : '0%';
      }
      handle.style.left = pct;

      // ARIA
      handle.setAttribute('aria-valuenow', pos);
      handle.setAttribute('aria-valuetext', labels[pos] || String(pos));

      // Update video div attributes
      videoDiv.setAttribute('data-skin', activeSkin);
      videoDiv.setAttribute('data-position', pos);

      // Render skin picker buttons
      renderSkinPicker();
    }

    function renderSkinPicker() {
      var skins = getAvailableSkins(lang, unlockedTier);
      skinPicker.innerHTML = '';

      if (skins.length <= 1) {
        skinPicker.style.display = 'none';
        return;
      }

      skinPicker.style.display = 'flex';
      skins.forEach(function (skin) {
        var btn = document.createElement('button');
        btn.className = 'skin-btn' + (skin === activeSkin ? ' active' : '');
        btn.textContent = SKIN_EMOJIS[skin] || skin;
        btn.setAttribute('aria-label', skin);
        btn.addEventListener('click', function () {
          activeSkin = skin;
          localStorage.setItem('cc-skin', skin);
          render();
        });
        skinPicker.appendChild(btn);
      });
    }

    function getSkinData(skin, l) {
      var s = SKINS[skin];
      if (!s) s = SKINS.cat;
      return s[l] || s.en;
    }

    function getAvailableSkins(l, tier) {
      var m = LANG_ANIMALS[l] || LANG_ANIMALS.en;
      var list = [m.default];
      if (tier >= 1) list.push(m.tier1);
      if (tier >= 2) {
        var t2 = m.tier2;
        if (Array.isArray(t2)) {
          // Pick randomly once (use stored or pick new)
          var stored = localStorage.getItem('cc-tier2-skin');
          if (stored && t2.indexOf(stored) !== -1) {
            list.push(stored);
          } else {
            var pick = t2[Math.floor(Math.random() * t2.length)];
            localStorage.setItem('cc-tier2-skin', pick);
            list.push(pick);
          }
        } else {
          list.push(t2);
        }
      }
      return list;
    }

    // ── POSITION CHANGE ───────────────────────────────────────────────────────

    function setPos(newPos) {
      newPos = Math.max(0, Math.min(2, newPos));
      pos = newPos;
      localStorage.setItem('cc-adventure-level', pos);
      render();
    }

    function posFromX(clientX) {
      var rect = handle.parentElement.getBoundingClientRect();
      var fraction = (clientX - rect.left) / rect.width;
      fraction = Math.max(0, Math.min(1, fraction));
      if (isRTL) fraction = 1 - fraction;
      if (fraction < 0.33) return 0;
      if (fraction < 0.67) return 1;
      return 2;
    }

    // ── EVENTS ────────────────────────────────────────────────────────────────

    var track = wrapper.querySelector('.slider-track');

    // Click on track
    track.addEventListener('click', function (e) {
      setPos(posFromX(e.clientX));
    });

    // Keyboard on handle
    handle.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
        e.preventDefault();
        setPos(isRTL ? pos - 1 : pos + 1);
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
        e.preventDefault();
        setPos(isRTL ? pos + 1 : pos - 1);
      } else if (e.key === 'Home') {
        e.preventDefault();
        setPos(0);
      } else if (e.key === 'End') {
        e.preventDefault();
        setPos(2);
      }
    });

    // Touch support
    var touchStartX = null;
    track.addEventListener('touchstart', function (e) {
      touchStartX = e.touches[0].clientX;
    }, { passive: true });

    track.addEventListener('touchmove', function (e) {
      if (touchStartX !== null) {
        setPos(posFromX(e.touches[0].clientX));
      }
    }, { passive: true });

    track.addEventListener('touchend', function () {
      touchStartX = null;
    }, { passive: true });

    // ── UNLOCK OBSERVERS ─────────────────────────────────────────────────────

    function unlockTier(tier) {
      if (unlockedTier >= tier) return; // already unlocked
      unlockedTier = tier;
      localStorage.setItem('cc-unlocked-tier', tier);

      var toastMsg = '';
      var tl = TOASTS[lang] || TOASTS.en;

      if (tier === 1) {
        toastMsg = tl.tier1;
        // Switch to rat skin automatically
        activeSkin = (LANG_ANIMALS[lang] || LANG_ANIMALS.en).tier1;
        localStorage.setItem('cc-skin', activeSkin);
      } else if (tier === 2) {
        var t2skins = getAvailableSkins(lang, 2);
        var t2skin = t2skins[t2skins.length - 1];
        var emoji = SKIN_EMOJIS[t2skin] || '';
        var name = (SKIN_NAMES[t2skin] && SKIN_NAMES[t2skin][lang]) || t2skin;
        toastMsg = tl.tier2(emoji, name);
        activeSkin = t2skin;
        localStorage.setItem('cc-skin', activeSkin);
      }

      if (toastMsg) showToast(toastMsg);
      render();
    }

    function observeUnlocks() {
      // Tier 1: FAQ heading scrolls into view
      var faqEl = document.getElementById('faq') || document.querySelector('[id="faq"]');
      // Tier 2: footer scrolls into view
      var footerEl = document.querySelector('footer') || document.querySelector('.footer');

      if (!('IntersectionObserver' in window)) return;

      if (faqEl && unlockedTier < 1) {
        var obs1 = new IntersectionObserver(function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              unlockTier(1);
              obs1.disconnect();
            }
          });
        }, { threshold: 0.1 });
        obs1.observe(faqEl);
      }

      if (footerEl && unlockedTier < 2) {
        var obs2 = new IntersectionObserver(function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              unlockTier(2);
              obs2.disconnect();
            }
          });
        }, { threshold: 0.1 });
        obs2.observe(footerEl);
      }
    }

    // ── INIT ──────────────────────────────────────────────────────────────────

    render();
    observeUnlocks();
  }

  // ── BOOT ──────────────────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', function () {
    var sliders = document.querySelectorAll('.adventure-slider');
    for (var i = 0; i < sliders.length; i++) {
      initSlider(sliders[i]);
    }
  });

}());
