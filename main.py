import os, random, sqlite3, logging, asyncio, aiohttp
from datetime import date, datetime, time, timezone
from functools import wraps
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN       = os.environ.get("BOT_TOKEN")
DB_PATH     = "muslim_bot.db"
QURAN_API   = "https://api.alquran.cloud/v1"
ALADHAN_API = "https://api.aladhan.com/v1"
SUPER_ADMINS: set[int] = {7851290806}

SURAH_NAMES = {
    1:"الفاتحة",2:"البقرة",3:"آل عمران",4:"النساء",5:"المائدة",
    6:"الأنعام",7:"الأعراف",8:"الأنفال",9:"التوبة",10:"يونس",
    11:"هود",12:"يوسف",13:"الرعد",14:"إبراهيم",15:"الحجر",
    16:"النحل",17:"الإسراء",18:"الكهف",19:"مريم",20:"طه",
    21:"الأنبياء",22:"الحج",23:"المؤمنون",24:"النور",25:"الفرقان",
    26:"الشعراء",27:"النمل",28:"القصص",29:"العنكبوت",30:"الروم",
    31:"لقمان",32:"السجدة",33:"الأحزاب",34:"سبأ",35:"فاطر",
    36:"يس",37:"الصافات",38:"ص",39:"الزمر",40:"غافر",
    41:"فصلت",42:"الشورى",43:"الزخرف",44:"الدخان",45:"الجاثية",
    46:"الأحقاف",47:"محمد",48:"الفتح",49:"الحجرات",50:"ق",
    51:"الذاريات",52:"الطور",53:"النجم",54:"القمر",55:"الرحمن",
    56:"الواقعة",57:"الحديد",58:"المجادلة",59:"الحشر",60:"الممتحنة",
    61:"الصف",62:"الجمعة",63:"المنافقون",64:"التغابن",65:"الطلاق",
    66:"التحريم",67:"الملك",68:"القلم",69:"الحاقة",70:"المعارج",
    71:"نوح",72:"الجن",73:"المزمل",74:"المدثر",75:"القيامة",
    76:"الإنسان",77:"المرسلات",78:"النبأ",79:"النازعات",80:"عبس",
    81:"التكوير",82:"الانفطار",83:"المطففين",84:"الانشقاق",85:"البروج",
    86:"الطارق",87:"الأعلى",88:"الغاشية",89:"الفجر",90:"البلد",
    91:"الشمس",92:"الليل",93:"الضحى",94:"الشرح",95:"التين",
    96:"العلق",97:"القدر",98:"البينة",99:"الزلزلة",100:"العاديات",
    101:"القارعة",102:"التكاثر",103:"العصر",104:"الهمزة",105:"الفيل",
    106:"قريش",107:"الماعون",108:"الكوثر",109:"الكافرون",110:"النصر",
    111:"المسد",112:"الإخلاص",113:"الفلق",114:"الناس",
}

SURAH_AYAH_COUNT = {
    1:7,2:286,3:200,4:176,5:120,6:165,7:206,8:75,9:129,10:109,
    11:123,12:111,13:43,14:52,15:99,16:128,17:111,18:110,19:98,20:135,
    21:112,22:78,23:118,24:64,25:77,26:227,27:93,28:88,29:69,30:60,
    31:34,32:30,33:73,34:54,35:45,36:83,37:182,38:88,39:75,40:85,
    41:54,42:53,43:89,44:59,45:37,46:35,47:38,48:29,49:18,50:45,
    51:60,52:49,53:62,54:55,55:78,56:96,57:29,58:22,59:24,60:13,
    61:14,62:11,63:11,64:18,65:12,66:12,67:30,68:52,69:52,70:44,
    71:28,72:28,73:20,74:56,75:40,76:31,77:50,78:40,79:46,80:42,
    81:29,82:19,83:36,84:25,85:22,86:17,87:19,88:26,89:30,90:20,
    91:15,92:21,93:11,94:8,95:8,96:19,97:5,98:8,99:8,100:11,
    101:11,102:8,103:3,104:9,105:5,106:4,107:7,108:3,109:6,110:3,
    111:5,112:4,113:5,114:6,
}

MORNING_ADHKAR = [
    ("اللّهُ لاَ إِلَـهَ إِلاَّ هُوَ الْحَيُّ الْقَيُّومُ لاَ تَأْخُذُهُ سِنَةٌ وَلاَ نَوْمٌ لَّهُ مَا فِي السَّمَاوَاتِ وَمَا فِي الأَرْضِ مَن ذَا الَّذِي يَشْفَعُ عِنْدَهُ إِلاَّ بِإِذْنِهِ يَعْلَمُ مَا بَيْنَ أَيْدِيهِمْ وَمَا خَلْفَهُمْ وَلاَ يُحِيطُونَ بِشَيْءٍ مِّنْ عِلْمِهِ إِلاَّ بِمَا شَاء وَسِعَ كُرْسِيُّهُ السَّمَاوَاتِ وَالأَرْضَ وَلاَ يَؤُودُهُ حِفْظُهُمَا وَهُوَ الْعَلِيُّ الْعَظِيمُ\n[البقرة: 255] — آية الكرسي", "١ مرة — من قالها حين يصبح أُجير من الجن حتى يمسي", 1),
    ("أَصْبَحْنَا وَأَصْبَحَ الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ، لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ، رَبِّ أَسْأَلُكَ خَيْرَ مَا فِي هَذَا الْيَوْمِ وَخَيْرَ مَا بَعْدَهُ، وَأَعُوذُ بِكَ مِنْ شَرِّ مَا فِي هَذَا الْيَوْمِ وَشَرِّ مَا بَعْدَهُ.", "١ مرة — رواه مسلم", 1),
    ("اللَّهُمَّ بِكَ أَصْبَحْنَا، وَبِكَ أَمْسَيْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ النُّشُورُ.", "١ مرة — رواه الترمذي", 1),
    ("اللَّهُمَّ أَنْتَ رَبِّي لَا إِلَهَ إِلَّا أَنْتَ، خَلَقْتَنِي وَأَنَا عَبْدُكَ، وَأَنَا عَلَى عَهْدِكَ وَوَعْدِكَ مَا اسْتَطَعْتُ، أَعُوذُ بِكَ مِنْ شَرِّ مَا صَنَعْتُ، أَبُوءُ لَكَ بِنِعْمَتِكَ عَلَيَّ، وَأَبُوءُ بِذَنْبِي فَاغْفِرْ لِي فَإِنَّهُ لَا يَغْفِرُ الذُّنُوبَ إِلَّا أَنْتَ.", "١ مرة — سيد الاستغفار | رواه البخاري", 1),
    ("اللَّهُمَّ إِنِّي أَصْبَحْتُ أُشْهِدُكَ، وَأُشْهِدُ حَمَلَةَ عَرْشِكَ، وَمَلَائِكَتَكَ، وَجَمِيعَ خَلْقِكَ، أَنَّكَ أَنْتَ اللَّهُ لَا إِلَهَ إِلَّا أَنْتَ وَحْدَكَ لَا شَرِيكَ لَكَ، وَأَنَّ مُحَمَّدًا عَبْدُكَ وَرَسُولُكَ.", "٤ مرات — رواه أبو داود", 4),
    ("اللَّهُمَّ مَا أَصْبَحَ بِي مِنْ نِعْمَةٍ أَوْ بِأَحَدٍ مِنْ خَلْقِكَ، فَمِنْكَ وَحْدَكَ لَا شَرِيكَ لَكَ، فَلَكَ الْحَمْدُ وَلَكَ الشُّكْرُ.", "١ مرة — رواه أبو داود", 1),
    ("اللَّهُمَّ عَافِنِي فِي بَدَنِي، اللَّهُمَّ عَافِنِي فِي سَمْعِي، اللَّهُمَّ عَافِنِي فِي بَصَرِي، لَا إِلَهَ إِلَّا أَنْتَ.\nاللَّهُمَّ إِنِّي أَعُوذُ بِكَ مِنَ الْكُفْرِ وَالْفَقْرِ، وَأَعُوذُ بِكَ مِنْ عَذَابِ الْقَبْرِ، لَا إِلَهَ إِلَّا أَنْتَ.", "٣ مرات — رواه أبو داود", 3),
    ("حَسْبِيَ اللَّهُ لَا إِلَهَ إِلَّا هُوَ، عَلَيْهِ تَوَكَّلْتُ وَهُوَ رَبُّ الْعَرْشِ الْعَظِيمِ.", "٧ مرات — رواه أبو داود", 7),
    ("بِسْمِ اللَّهِ الَّذِي لَا يَضُرُّ مَعَ اسْمِهِ شَيْءٌ فِي الْأَرْضِ وَلَا فِي السَّمَاءِ وَهُوَ السَّمِيعُ الْعَلِيمُ.", "٣ مرات — رواه أبو داود والترمذي", 3),
    ("رَضِيتُ بِاللَّهِ رَبًّا، وَبِالْإِسْلَامِ دِينًا، وَبِمُحَمَّدٍ صلى الله عليه وسلم نَبِيًّا.", "٣ مرات — رواه أبو داود", 3),
    ("سُبْحَانَ اللَّهِ وَبِحَمْدِهِ.", "١٠٠ مرة — رواه مسلم", 100),
    ("لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ، وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ.", "١٠ مرات — رواه أحمد", 10),
    ("اللَّهُمَّ إِنِّي أَسْأَلُكَ الْعَفْوَ وَالْعَافِيَةَ فِي الدُّنْيَا وَالْآخِرَةِ.\nاللَّهُمَّ اسْتُرْ عَوْرَاتِي وَآمِنْ رَوْعَاتِي.\nاللَّهُمَّ احْفَظْنِي مِنْ بَيْنِ يَدَيَّ وَمِنْ خَلْفِي وَعَنْ يَمِينِي وَعَنْ شِمَالِي وَمِنْ فَوْقِي.", "١ مرة — رواه أبو داود وابن ماجه", 1),
    ("قُلْ هُوَ اللَّهُ أَحَدٌ — قُلْ أَعُوذُ بِرَبِّ الْفَلَقِ — قُلْ أَعُوذُ بِرَبِّ النَّاسِ", "٣ مرات لكل سورة — رواه أبو داود والترمذي", 3),
]

EVENING_ADHKAR = [
    ("اللَّهُ لَا إِلَهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ لَا تَأْخُذُهُ سِنَةٌ وَلَا نَوْمٌ\n[البقرة: 255] — آية الكرسي", "١ مرة — من قالها حين يمسي أُجير من الجن حتى يصبح", 1),
    ("أَمْسَيْنَا وَأَمْسَى الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ، لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ.", "١ مرة — رواه مسلم", 1),
    ("اللَّهُمَّ بِكَ أَمْسَيْنَا، وَبِكَ أَصْبَحْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ الْمَصِيرُ.", "١ مرة — رواه الترمذي", 1),
    ("اللَّهُمَّ أَنْتَ رَبِّي لَا إِلَهَ إِلَّا أَنْتَ — سيد الاستغفار.", "١ مرة — رواه البخاري", 1),
    ("أَعُوذُ بِكَلِمَاتِ اللَّهِ التَّامَّاتِ مِنْ شَرِّ مَا خَلَقَ.", "٣ مرات — رواه مسلم", 3),
    ("بِسْمِ اللَّهِ الَّذِي لَا يَضُرُّ مَعَ اسْمِهِ شَيْءٌ فِي الْأَرْضِ وَلَا فِي السَّمَاءِ وَهُوَ السَّمِيعُ الْعَلِيمُ.", "٣ مرات — رواه أبو داود", 3),
    ("حَسْبِيَ اللَّهُ لَا إِلَهَ إِلَّا هُوَ، عَلَيْهِ تَوَكَّلْتُ وَهُوَ رَبُّ الْعَرْشِ الْعَظِيمِ.", "٧ مرات — رواه أبو داود", 7),
    ("سُبْحَانَ اللَّهِ وَبِحَمْدِهِ.", "١٠٠ مرة — رواه مسلم", 100),
    ("اللَّهُمَّ إِنِّي أَمْسَيْتُ أُشْهِدُكَ وَأُشْهِدُ حَمَلَةَ عَرْشِكَ.", "٤ مرات — رواه أبو داود", 4),
    ("قُلْ هُوَ اللَّهُ أَحَدٌ — قُلْ أَعُوذُ بِرَبِّ الْفَلَقِ — قُلْ أَعُوذُ بِرَبِّ النَّاسِ", "٣ مرات لكل سورة", 3),
]

SLEEP_ADHKAR = [
    ("بِاسْمِكَ رَبِّي وَضَعْتُ جَنْبِي، وَبِكَ أَرْفَعُهُ، فَإِنْ أَمْسَكْتَ نَفْسِي فَارْحَمْهَا، وَإِنْ أَرْسَلْتَهَا فَاحْفَظْهَا بِمَا تَحْفَظُ بِهِ عِبَادَكَ الصَّالِحِينَ.", "١ مرة — متفق عليه", 1),
    ("اللَّهُمَّ إِنَّكَ خَلَقْتَ نَفْسِي وَأَنْتَ تَوَفَّاهَا، لَكَ مَمَاتُهَا وَمَحْيَاهَا.", "١ مرة — رواه مسلم", 1),
    ("اللَّهُمَّ قِنِي عَذَابَكَ يَوْمَ تَبْعَثُ عِبَادَكَ.", "٣ مرات — رواه أبو داود", 3),
    ("بِاسْمِكَ اللَّهُمَّ أَمُوتُ وَأَحْيَا.", "١ مرة — رواه البخاري", 1),
    ("سُبْحَانَ اللَّهِ ٣٣ — الْحَمْدُ لِلَّهِ ٣٣ — اللَّهُ أَكْبَرُ ٣٤ — تسبيح فاطمة", "رواه البخاري ومسلم", 1),
    ("اللَّهُ لَا إِلَهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ... [البقرة: 255] — آية الكرسي", "١ مرة — رواه البخاري", 1),
    ("اللَّهُمَّ أَسْلَمْتُ نَفْسِي إِلَيْكَ، وَفَوَّضْتُ أَمْرِي إِلَيْكَ، وَوَجَّهْتُ وَجْهِي إِلَيْكَ، آمَنْتُ بِكِتَابِكَ الَّذِي أَنْزَلْتَ وَبِنَبِيِّكَ الَّذِي أَرْسَلْتَ.", "١ مرة — آخر كلام قبل النوم | متفق عليه", 1),
]

WAKEUP_ADHKAR = [
    ("الْحَمْدُ لِلَّهِ الَّذِي أَحْيَانَا بَعْدَ مَا أَمَاتَنَا وَإِلَيْهِ النُّشُورُ.", "١ مرة — رواه البخاري", 1),
    ("لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ، وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ، سُبْحَانَ اللَّهِ وَالْحَمْدُ لِلَّهِ وَلَا إِلَهَ إِلَّا اللَّهُ وَاللَّهُ أَكْبَرُ، رَبِّ اغْفِرْ لِي.", "١ مرة — رواه البخاري", 1),
]

WUDU_ADHKAR = [
    ("بِسْمِ اللَّهِ.", "عند البدء — رواه أبو داود", 1),
    ("أَشْهَدُ أَنْ لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ وَأَشْهَدُ أَنَّ مُحَمَّدًا عَبْدُهُ وَرَسُولُهُ، اللَّهُمَّ اجْعَلْنِي مِنَ التَّوَّابِينَ وَاجْعَلْنِي مِنَ الْمُتَطَهِّرِينَ.", "بعد الوضوء — رواه مسلم", 1),
    ("سُبْحَانَكَ اللَّهُمَّ وَبِحَمْدِكَ أَشْهَدُ أَنْ لَا إِلَهَ إِلَّا أَنْتَ أَسْتَغْفِرُكَ وَأَتُوبُ إِلَيْكَ.", "بعد الوضوء — رواه النسائي", 1),
]

PRAYER_ADHKAR = {
    "الأذان": [
        ("ترديد كلمات المؤذن. عند الحيعلتين: لَا حَوْلَ وَلَا قُوَّةَ إِلَّا بِاللَّهِ.", "رواه مسلم", 1),
        ("اللَّهُمَّ رَبَّ هَذِهِ الدَّعْوَةِ التَّامَّةِ وَالصَّلَاةِ الْقَائِمَةِ آتِ مُحَمَّدًا الْوَسِيلَةَ وَالْفَضِيلَةَ.", "بعد الأذان — رواه البخاري", 1),
    ],
    "دعاء الاستفتاح": [
        ("سُبْحَانَكَ اللَّهُمَّ وَبِحَمْدِكَ وَتَبَارَكَ اسْمُكَ وَتَعَالَى جَدُّكَ وَلَا إِلَهَ غَيْرُكَ.", "رواه الترمذي وأبو داود", 1),
    ],
    "ذكر الركوع": [
        ("سُبْحَانَ رَبِّيَ الْعَظِيمِ.", "٣ مرات — رواه مسلم", 3),
        ("سُبْحَانَكَ اللَّهُمَّ رَبَّنَا وَبِحَمْدِكَ اللَّهُمَّ اغْفِرْ لِي.", "رواه البخاري ومسلم", 1),
    ],
    "الرفع من الركوع": [
        ("سَمِعَ اللَّهُ لِمَنْ حَمِدَهُ — رَبَّنَا وَلَكَ الْحَمْدُ حَمْدًا كَثِيرًا طَيِّبًا مُبَارَكًا فِيهِ.", "رواه البخاري", 1),
    ],
    "ذكر السجود": [
        ("سُبْحَانَ رَبِّيَ الْأَعْلَى.", "٣ مرات — رواه مسلم", 3),
        ("اللَّهُمَّ اغْفِرْ لِي ذَنْبِي كُلَّهُ دِقَّهُ وَجِلَّهُ.", "رواه مسلم", 1),
    ],
    "الجلوس بين السجدتين": [
        ("رَبِّ اغْفِرْ لِي، رَبِّ اغْفِرْ لِي.", "رواه أبو داود", 1),
    ],
    "التشهد والصلاة الإبراهيمية": [
        ("التَّحِيَّاتُ لِلَّهِ وَالصَّلَوَاتُ وَالطَّيِّبَاتُ، السَّلَامُ عَلَيْكَ أَيُّهَا النَّبِيُّ وَرَحْمَةُ اللَّهِ وَبَرَكَاتُهُ، السَّلَامُ عَلَيْنَا وَعَلَى عِبَادِ اللَّهِ الصَّالِحِينَ، أَشْهَدُ أَنْ لَا إِلَهَ إِلَّا اللَّهُ وَأَشْهَدُ أَنَّ مُحَمَّدًا عَبْدُهُ وَرَسُولُهُ.", "متفق عليه", 1),
        ("اللَّهُمَّ صَلِّ عَلَى مُحَمَّدٍ وَعَلَى آلِ مُحَمَّدٍ كَمَا صَلَّيْتَ عَلَى إِبْرَاهِيمَ.", "متفق عليه", 1),
    ],
    "أذكار بعد الصلاة": [
        ("أَسْتَغْفِرُ اللَّهَ ٣ مرات — اللَّهُمَّ أَنْتَ السَّلَامُ وَمِنْكَ السَّلَامُ تَبَارَكْتَ يَا ذَا الْجَلَالِ وَالْإِكْرَامِ.", "رواه مسلم", 1),
        ("سُبْحَانَ اللَّهِ ٣٣ — الْحَمْدُ لِلَّهِ ٣٣ — اللَّهُ أَكْبَرُ ٣٣ — لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ.", "رواه مسلم", 1),
        ("قراءة آية الكرسي دبر كل صلاة مكتوبة.", "رواه النسائي", 1),
    ],
}

SPECIAL_DUAS = {
    "دعاء الهم والحزن": [
        ("اللَّهُمَّ إِنِّي عَبْدُكَ ابْنُ عَبْدِكَ ابْنُ أَمَتِكَ، نَاصِيَتِي بِيَدِكَ، مَاضٍ فِيَّ حُكْمُكَ، عَدْلٌ فِيَّ قَضَاؤُكَ، أَسْأَلُكَ بِكُلِّ اسْمٍ هُوَ لَكَ أَنْ تَجْعَلَ الْقُرْآنَ رَبِيعَ قَلْبِي.", "رواه أحمد", 1),
        ("لَا إِلَهَ إِلَّا اللَّهُ الْعَظِيمُ الْحَلِيمُ، لَا إِلَهَ إِلَّا اللَّهُ رَبُّ الْعَرْشِ الْعَظِيمِ.", "متفق عليه — دعاء الكرب", 1),
    ],
    "دعاء الكرب الشديد": [
        ("لَا إِلَهَ إِلَّا أَنْتَ سُبْحَانَكَ إِنِّي كُنْتُ مِنَ الظَّالِمِينَ.", "دعاء ذي النون — الأنبياء: ٨٧", 1),
    ],
    "دعاء الاستغفار": [
        ("أَسْتَغْفِرُ اللَّهَ الَّذِي لَا إِلَهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ وَأَتُوبُ إِلَيْهِ.", "رواه الترمذي", 1),
        ("رَبِّ اغْفِرْ لِي وَتُبْ عَلَيَّ إِنَّكَ أَنْتَ التَّوَّابُ الرَّحِيمُ.", "١٠٠ مرة — رواه الترمذي", 100),
    ],
    "دعاء طلب الرزق": [
        ("اللَّهُمَّ اكْفِنِي بِحَلَالِكَ عَنْ حَرَامِكَ وَأَغْنِنِي بِفَضْلِكَ عَمَّنْ سِوَاكَ.", "رواه الترمذي", 1),
    ],
    "دعاء الشفاء": [
        ("اللَّهُمَّ رَبَّ النَّاسِ أَذْهِبِ الْبَأْسَ، اشْفِ أَنْتَ الشَّافِي، لَا شِفَاءَ إِلَّا شِفَاؤُكَ.", "متفق عليه", 1),
        ("أَسْأَلُ اللَّهَ الْعَظِيمَ رَبَّ الْعَرْشِ الْعَظِيمِ أَنْ يَشْفِيَكَ.", "٧ مرات — رواه الترمذي", 7),
    ],
    "دعاء عند البلاء": [
        ("إِنَّا لِلَّهِ وَإِنَّا إِلَيْهِ رَاجِعُونَ، اللَّهُمَّ أْجُرْنِي فِي مُصِيبَتِي وَأَخْلِفْ لِي خَيْرًا مِنْهَا.", "رواه مسلم", 1),
    ],
}

TASBIH_LIST = [
    ("سُبْحَانَ اللَّهِ",                                             "تمحو الخطايا كما تتساقط أوراق الشجر — رواه مسلم",                  33),
    ("الْحَمْدُ لِلَّهِ",                                             "تملأ الميزان يوم القيامة — رواه مسلم",                              33),
    ("اللَّهُ أَكْبَرُ",                                              "تملأ ما بين السماء والأرض بالحسنات",                                33),
    ("لَا إِلَهَ إِلَّا اللَّهُ",                                     "أفضل الذكر وأحبه إلى الله — رواه الترمذي",                         100),
    ("لَا حَوْلَ وَلَا قُوَّةَ إِلَّا بِاللَّهِ",                   "كنز من كنوز الجنة — متفق عليه",                                    100),
    ("سُبْحَانَ اللَّهِ وَبِحَمْدِهِ سُبْحَانَ اللَّهِ الْعَظِيمِ", "أحب الكلام إلى الله وأثقله في الميزان — متفق عليه",                100),
    ("أَسْتَغْفِرُ اللَّهَ",                                          "من لزمها فتح الله له من كل ضيق مخرجا — رواه أبو داود",             100),
    ("اللَّهُمَّ صَلِّ وَسَلِّمْ عَلَى نَبِيِّنَا مُحَمَّدٍ",      "من صلى على النبي مرة صلى الله عليه عشرا — رواه مسلم",              100),
    ("سُبْحَانَ اللَّهِ وَبِحَمْدِهِ",                               "من قالها مئة مرة غُفرت خطاياه وإن كانت مثل زبد البحر — البخاري",  100),
    ("اللَّهُمَّ اغْفِرْ لِي وَتُبْ عَلَيَّ",                       "رواه أبو داود — قالها النبي ﷺ مئة مرة في المجلس",                   100),
]

FRIDAY_SUNNAN = [
    {"title": "🛁 الاغتسال",        "text": "الاغتسال يوم الجمعة واجب على كل محتلم.\nقال النبي ﷺ: غسل الجمعة واجب على كل محتلم.",                                        "source": "متفق عليه"},
    {"title": "⏰ التبكير",          "text": "التبكير إلى صلاة الجمعة.\nمن راح في الساعة الأولى فكأنما قرّب بدنة، والثانية بقرة، والثالثة كبشاً.",                     "source": "متفق عليه"},
    {"title": "🤲 الصلاة على النبي", "text": "أَكْثِرُوا الصَّلَاةَ عَلَيَّ يَوْمَ الجُمُعَةِ وَلَيْلَةَ الجُمُعَةِ، فَمَنْ صَلَّى عَلَيَّ صَلَاةً صَلَّى اللَّهُ عَلَيْهِ عَشْرًا.", "source": "رواه البيهقي"},
    {"title": "⭐ ساعة الاستجابة", "text": "في يوم الجمعة ساعة لا يوافقها عبد مسلم وهو قائم يصلي يسأل الله شيئاً إلا أعطاه.\nأرجح الأقوال: آخر ساعة بعد العصر حتى المغرب.", "source": "متفق عليه"},
]

FRIDAY_SURAHS = {
    18: "📖 الكهف — أضاء له النور ما بين الجمعتين",
    36: "📖 يس — قلب القرآن",
    67: "📖 الملك — تشفع لصاحبها في القبر",
}

ALGERIAN_CITIES = [
    "Algiers","Oran","Constantine","Annaba","Blida","Batna","Sétif",
    "Sidi Bel Abbès","Biskra","Béjaïa","Tlemcen","Béchar","Mostaganem",
    "Skikda","Chlef","Souk Ahras","Tiaret","M'Sila","Djelfa","Tizi Ouzou",
    "Ouargla","Ghardaïa","El Oued","Tamanrasset","Adrar",
]

MOTIVATION_MSGS = [
    "🌺 ما شاء الله تبارك الله! أتممت هذا الذكر.\nقال النبي ﷺ: أحب الأعمال إلى الله أدومها وإن قلّ.",
    "🌟 بارك الله فيك! كل كلمة طيبة شجرة في الجنة.\nاستمر فإن الملائكة تكتب حسناتك الآن.",
    "💫 رائع! قال تعالى: ﴿أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ﴾\nأنت على الطريق الصحيح.",
    "🌸 جزاك الله خيراً! المواظبة على الذكر نور في القلب ونور في القبر.",
    "🤲 اللهم تقبّل منك! قال ﷺ: كلمتان خفيفتان على اللسان ثقيلتان في الميزان: سبحان الله وبحمده.",
    "✨ أحسنت! إن الذاكرين الله كثيراً والذاكرات أعدّ الله لهم مغفرة وأجراً عظيماً.",
]

ADHKAR_MAP = {
    "morning": ("🌅 أذكار الصباح",   MORNING_ADHKAR),
    "evening": ("🌆 أذكار المساء",    EVENING_ADHKAR),
    "sleep":   ("🌙 أذكار النوم",     SLEEP_ADHKAR),
    "wakeup":  ("🌺 أذكار الاستيقاظ", WAKEUP_ADHKAR),
    "wudu":    ("💧 أذكار الوضوء",    WUDU_ADHKAR),
}

# ══════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════
def init_db():
    con = sqlite3.connect(DB_PATH)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
            last_name TEXT, joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_admin INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0,
            last_seen TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS hadiths (
            id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL,
            source TEXT NOT NULL, added_by INTEGER, added_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS duas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL,
            source TEXT NOT NULL, added_by INTEGER, added_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS wird_progress (
            user_id INTEGER PRIMARY KEY, surah INTEGER NOT NULL DEFAULT 2, ayah INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS surah_progress (
            user_id INTEGER NOT NULL, surah INTEGER NOT NULL,
            riwaya TEXT NOT NULL DEFAULT 'hafs', last_ayah INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (user_id, surah, riwaya)
        );
        CREATE TABLE IF NOT EXISTS tasbih_log (
            user_id INTEGER NOT NULL, log_date TEXT NOT NULL,
            phrase TEXT NOT NULL, count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, log_date, phrase)
        );
        CREATE TABLE IF NOT EXISTS adhkar_progress (
            user_id INTEGER NOT NULL, adhkar_key TEXT NOT NULL,
            idx INTEGER NOT NULL DEFAULT 0, counter INTEGER NOT NULL DEFAULT 0,
            done_date TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (user_id, adhkar_key)
        );
        CREATE TABLE IF NOT EXISTS inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            username TEXT, first_name TEXT, message TEXT NOT NULL,
            reply TEXT, status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP, replied_at TEXT
        );
        CREATE TABLE IF NOT EXISTS prayer_cities (
            user_id INTEGER PRIMARY KEY, city TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            action TEXT NOT NULL, detail TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS bot_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL,
            text TEXT NOT NULL, source TEXT NOT NULL,
            added_by INTEGER, added_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS notifications_sent (
            user_id INTEGER NOT NULL, notif_key TEXT NOT NULL,
            sent_date TEXT NOT NULL, PRIMARY KEY (user_id, notif_key, sent_date)
        );
        CREATE TABLE IF NOT EXISTS tasbih_session (
            user_id INTEGER NOT NULL, phrase_idx INTEGER NOT NULL DEFAULT 0,
            counter INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (user_id)
        );
        CREATE TABLE IF NOT EXISTS dynamic_buttons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER DEFAULT NULL,
            section TEXT NOT NULL DEFAULT 'root',
            btn_label TEXT NOT NULL,
            btn_type TEXT NOT NULL DEFAULT 'text',
            btn_content TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            added_by INTEGER,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS notif_settings (
            user_id INTEGER PRIMARY KEY,
            morning_on INTEGER DEFAULT 1,
            evening_on INTEGER DEFAULT 1,
            wird_on    INTEGER DEFAULT 1,
            friday_on  INTEGER DEFAULT 1
        );
    """)
    con.commit(); con.close()

# ── DB helpers ─────────────────────────────────────────────────────
def upsert_user(uid, username, first_name, last_name=None):
    con = sqlite3.connect(DB_PATH)
    con.execute("""INSERT INTO users(user_id,username,first_name,last_name,last_seen)
        VALUES(?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
        username=excluded.username,first_name=excluded.first_name,
        last_name=excluded.last_name,last_seen=excluded.last_seen""",
        (uid,username,first_name,last_name,datetime.now().isoformat()))
    con.commit(); con.close()

def is_admin(uid):
    if uid in SUPER_ADMINS: return True
    con=sqlite3.connect(DB_PATH); row=con.execute("SELECT is_admin FROM users WHERE user_id=?",(uid,)).fetchone(); con.close()
    return bool(row and row[0])

def is_banned(uid):
    con=sqlite3.connect(DB_PATH); row=con.execute("SELECT is_banned FROM users WHERE user_id=?",(uid,)).fetchone(); con.close()
    return bool(row and row[0])

def get_random_hadith():
    con=sqlite3.connect(DB_PATH); row=con.execute("SELECT text,source FROM hadiths ORDER BY RANDOM() LIMIT 1").fetchone(); con.close(); return row

def get_random_dua():
    con=sqlite3.connect(DB_PATH); row=con.execute("SELECT text,source FROM duas ORDER BY RANDOM() LIMIT 1").fetchone(); con.close(); return row

def save_wird_progress(uid,surah,ayah):
    con=sqlite3.connect(DB_PATH); con.execute("INSERT INTO wird_progress(user_id,surah,ayah) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET surah=excluded.surah,ayah=excluded.ayah",(uid,surah,ayah)); con.commit(); con.close()

def get_wird_progress(uid):
    con=sqlite3.connect(DB_PATH); row=con.execute("SELECT surah,ayah FROM wird_progress WHERE user_id=?",(uid,)).fetchone(); con.close(); return (row[0],row[1]) if row else (2,1)

def save_surah_progress(uid,surah,ayah,riwaya="hafs"):
    con=sqlite3.connect(DB_PATH); con.execute("INSERT INTO surah_progress(user_id,surah,riwaya,last_ayah) VALUES(?,?,?,?) ON CONFLICT(user_id,surah,riwaya) DO UPDATE SET last_ayah=excluded.last_ayah",(uid,surah,riwaya,ayah)); con.commit(); con.close()

def get_surah_progress(uid,surah,riwaya="hafs"):
    con=sqlite3.connect(DB_PATH); row=con.execute("SELECT last_ayah FROM surah_progress WHERE user_id=? AND surah=? AND riwaya=?",(uid,surah,riwaya)).fetchone(); con.close(); return row[0] if row else 1

def log_tasbih(uid,phrase,count):
    con=sqlite3.connect(DB_PATH); con.execute("INSERT INTO tasbih_log(user_id,log_date,phrase,count) VALUES(?,?,?,?) ON CONFLICT(user_id,log_date,phrase) DO UPDATE SET count=count+excluded.count",(uid,date.today().isoformat(),phrase,count)); con.commit(); con.close()

def get_tasbih_stats(uid):
    con=sqlite3.connect(DB_PATH)
    rows=con.execute("SELECT phrase,SUM(count) FROM tasbih_log WHERE user_id=? GROUP BY phrase ORDER BY SUM(count) DESC LIMIT 5",(uid,)).fetchall()
    total=con.execute("SELECT SUM(count) FROM tasbih_log WHERE user_id=?",(uid,)).fetchone()[0] or 0
    con.close(); return total,rows

def save_tasbih_session(uid,pidx,counter):
    con=sqlite3.connect(DB_PATH); con.execute("INSERT INTO tasbih_session(user_id,phrase_idx,counter) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET phrase_idx=excluded.phrase_idx,counter=excluded.counter",(uid,pidx,counter)); con.commit(); con.close()

def save_adhkar_progress(uid,key,idx,counter=0):
    con=sqlite3.connect(DB_PATH); con.execute("INSERT INTO adhkar_progress(user_id,adhkar_key,idx,counter,done_date) VALUES(?,?,?,?,?) ON CONFLICT(user_id,adhkar_key) DO UPDATE SET idx=excluded.idx,counter=excluded.counter,done_date=excluded.done_date",(uid,key,idx,counter,date.today().isoformat())); con.commit(); con.close()

def get_adhkar_progress(uid,key):
    con=sqlite3.connect(DB_PATH); row=con.execute("SELECT idx,counter,done_date FROM adhkar_progress WHERE user_id=? AND adhkar_key=?",(uid,key)).fetchone(); con.close()
    if row and row[2]==date.today().isoformat(): return row[0],row[1]
    return 0,0

def log_activity(uid,action,detail=""):
    con=sqlite3.connect(DB_PATH); con.execute("INSERT INTO activities(user_id,action,detail) VALUES(?,?,?)",(uid,action,detail)); con.commit(); con.close()

def get_user_full_stats(uid):
    surah,ayah=get_wird_progress(uid); total_t,tsb=get_tasbih_stats(uid)
    con=sqlite3.connect(DB_PATH)
    inq=con.execute("SELECT COUNT(*) FROM inquiries WHERE user_id=?",(uid,)).fetchone()[0]
    sdn=con.execute("SELECT COUNT(DISTINCT surah) FROM surah_progress WHERE user_id=?",(uid,)).fetchone()[0]
    con.close(); return {"wird_surah":surah,"wird_ayah":ayah,"total_t":total_t,"inquiries":inq,"surahs_done":sdn}

def get_all_users():
    con=sqlite3.connect(DB_PATH); rows=con.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall(); con.close(); return [r[0] for r in rows]

def get_all_admins():
    con=sqlite3.connect(DB_PATH); rows=con.execute("SELECT user_id FROM users WHERE is_admin=1").fetchall(); con.close()
    return list(set([r[0] for r in rows]+list(SUPER_ADMINS)))

def save_inquiry(uid,username,first_name,message):
    con=sqlite3.connect(DB_PATH); cur=con.execute("INSERT INTO inquiries(user_id,username,first_name,message) VALUES(?,?,?,?)",(uid,username,first_name,message)); iid=cur.lastrowid; con.commit(); con.close(); return iid

def get_pending_inquiries():
    con=sqlite3.connect(DB_PATH); rows=con.execute("SELECT id,user_id,username,first_name,message,created_at FROM inquiries WHERE status='pending' ORDER BY created_at DESC").fetchall(); con.close(); return rows

def get_all_inquiries(limit=20):
    con=sqlite3.connect(DB_PATH); rows=con.execute("SELECT id,user_id,username,first_name,message,status,created_at FROM inquiries ORDER BY created_at DESC LIMIT ?",(limit,)).fetchall(); con.close(); return rows

def reply_to_inquiry(iid,reply_text):
    con=sqlite3.connect(DB_PATH); row=con.execute("SELECT user_id FROM inquiries WHERE id=?",(iid,)).fetchone()
    con.execute("UPDATE inquiries SET reply=?,status='replied',replied_at=CURRENT_TIMESTAMP WHERE id=?",(reply_text,iid)); con.commit(); con.close(); return row[0] if row else None

def save_user_city(uid,city):
    con=sqlite3.connect(DB_PATH); con.execute("INSERT INTO prayer_cities(user_id,city) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET city=excluded.city",(uid,city)); con.commit(); con.close()

def get_user_city(uid):
    con=sqlite3.connect(DB_PATH); row=con.execute("SELECT city FROM prayer_cities WHERE user_id=?",(uid,)).fetchone(); con.close(); return row[0] if row else None

def ban_user(uid):
    con=sqlite3.connect(DB_PATH); con.execute("UPDATE users SET is_banned=1 WHERE user_id=?",(uid,)); con.commit(); con.close()

def unban_user(uid):
    con=sqlite3.connect(DB_PATH); con.execute("UPDATE users SET is_banned=0 WHERE user_id=?",(uid,)); con.commit(); con.close()

def mark_notif_sent(uid,key):
    con=sqlite3.connect(DB_PATH)
    try: con.execute("INSERT INTO notifications_sent(user_id,notif_key,sent_date) VALUES(?,?,?)",(uid,key,date.today().isoformat())); con.commit()
    except: pass
    con.close()

def notif_already_sent(uid,key):
    con=sqlite3.connect(DB_PATH); row=con.execute("SELECT 1 FROM notifications_sent WHERE user_id=? AND notif_key=? AND sent_date=?",(uid,key,date.today().isoformat())).fetchone(); con.close(); return bool(row)

def get_admin_stats():
    con=sqlite3.connect(DB_PATH); today=date.today().isoformat()
    s={
        "users":        con.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "admins":       con.execute("SELECT COUNT(*) FROM users WHERE is_admin=1").fetchone()[0],
        "banned":       con.execute("SELECT COUNT(*) FROM users WHERE is_banned=1").fetchone()[0],
        "active_today": con.execute("SELECT COUNT(DISTINCT user_id) FROM activities WHERE DATE(created_at)=?",(today,)).fetchone()[0],
        "hadiths":      con.execute("SELECT COUNT(*) FROM hadiths").fetchone()[0],
        "duas":         con.execute("SELECT COUNT(*) FROM duas").fetchone()[0],
        "tasbih_total": con.execute("SELECT SUM(count) FROM tasbih_log").fetchone()[0] or 0,
        "pending":      con.execute("SELECT COUNT(*) FROM inquiries WHERE status='pending'").fetchone()[0],
        "replied":      con.execute("SELECT COUNT(*) FROM inquiries WHERE status='replied'").fetchone()[0],
        "content":      con.execute("SELECT COUNT(*) FROM bot_content").fetchone()[0],
        "dyn_buttons":  con.execute("SELECT COUNT(*) FROM dynamic_buttons").fetchone()[0],
    }
    con.close(); return s

def get_users_list(limit=30):
    con=sqlite3.connect(DB_PATH); rows=con.execute("SELECT user_id,username,first_name,is_admin,is_banned,last_seen FROM users ORDER BY last_seen DESC LIMIT ?",(limit,)).fetchall(); con.close(); return rows

def get_notif_settings(uid):
    con=sqlite3.connect(DB_PATH); row=con.execute("SELECT morning_on,evening_on,wird_on,friday_on FROM notif_settings WHERE user_id=?",(uid,)).fetchone(); con.close()
    return {"morning":row[0],"evening":row[1],"wird":row[2],"friday":row[3]} if row else {"morning":1,"evening":1,"wird":1,"friday":1}

def set_notif_setting(uid,key,val):
    col=f"{key}_on"
    con=sqlite3.connect(DB_PATH); con.execute(f"INSERT INTO notif_settings(user_id,{col}) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET {col}=excluded.{col}",(uid,val)); con.commit(); con.close()

# ── Dynamic buttons DB ─────────────────────────────────────────────
def db_get_children(parent_id=None, section="root"):
    con=sqlite3.connect(DB_PATH)
    if parent_id is None:
        rows=con.execute("SELECT id,btn_label,btn_type,btn_content FROM dynamic_buttons WHERE parent_id IS NULL AND section=? ORDER BY sort_order,id",(section,)).fetchall()
    else:
        rows=con.execute("SELECT id,btn_label,btn_type,btn_content FROM dynamic_buttons WHERE parent_id=? ORDER BY sort_order,id",(parent_id,)).fetchall()
    con.close(); return rows

def db_get_btn(bid):
    con=sqlite3.connect(DB_PATH); row=con.execute("SELECT id,parent_id,section,btn_label,btn_type,btn_content FROM dynamic_buttons WHERE id=?",(bid,)).fetchone(); con.close(); return row

def db_add_btn(parent_id, section, label, btn_type, content, added_by):
    con=sqlite3.connect(DB_PATH)
    max_order=con.execute("SELECT COALESCE(MAX(sort_order),0) FROM dynamic_buttons WHERE parent_id IS ?",(parent_id,)).fetchone()[0]
    con.execute("INSERT INTO dynamic_buttons(parent_id,section,btn_label,btn_type,btn_content,sort_order,added_by) VALUES(?,?,?,?,?,?,?)",(parent_id,section,label,btn_type,content,max_order+1,added_by))
    con.commit(); con.close()

def db_del_btn(bid):
    con=sqlite3.connect(DB_PATH)
    # delete children recursively
    def _del(b):
        kids=con.execute("SELECT id FROM dynamic_buttons WHERE parent_id=?",(b,)).fetchall()
        for k in kids: _del(k[0])
        con.execute("DELETE FROM dynamic_buttons WHERE id=?",(b,))
    _del(bid); con.commit(); con.close()

def db_update_btn_label(bid, new_label):
    con=sqlite3.connect(DB_PATH); con.execute("UPDATE dynamic_buttons SET btn_label=? WHERE id=?",(new_label,bid)); con.commit(); con.close()

def db_update_btn_content(bid, new_content):
    con=sqlite3.connect(DB_PATH); con.execute("UPDATE dynamic_buttons SET btn_content=? WHERE id=?",(new_content,bid)); con.commit(); con.close()

# ══════════════════════════════════════════════════════════════════
# API HELPERS
# ══════════════════════════════════════════════════════════════════
async def fetch_dates():
    try:
        today=date.today().strftime("%d-%m-%Y"); now=datetime.now()
        days_ar=["الاثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","السبت","الأحد"]
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as s:
            async with s.get(f"{ALADHAN_API}/gToH/{today}") as r:
                data=await r.json(); h=data["data"]["hijri"]
                hijri=f"{h['day']} {h['month']['ar']} {h['year']} هـ"
        return f"📅 الهجري: *{hijri}*\n📆 الميلادي: *{now.strftime('%A, %d %B %Y')}*\n🌙 اليوم: *{days_ar[now.weekday()]}*"
    except: return f"📆 {datetime.now().strftime('%A, %d %B %Y')}"

async def fetch_prayer_times(city):
    try:
        today=date.today().strftime("%d-%m-%Y")
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(f"{ALADHAN_API}/timingsByCity/{today}",params={"city":city,"country":"DZ","method":3}) as r:
                data=await r.json()
        if data.get("code")!=200: return "⚠️ تعذّر جلب أوقات الصلاة."
        t=data["data"]["timings"]
        lines="\n".join([f"{n}: `{v}`" for n,v in [("🌅 الفجر",t.get("Fajr","—")),("☀️ الشروق",t.get("Sunrise","—")),("🌤 الظهر",t.get("Dhuhr","—")),("🌇 العصر",t.get("Asr","—")),("🌆 المغرب",t.get("Maghrib","—")),("🌃 العشاء",t.get("Isha","—"))]])
        return f"🕌 *أوقات الصلاة — {city}*\n\n{lines}\n\n_المصدر: aladhan.com_"
    except Exception as e: return f"⚠️ خطأ: {e}"

async def fetch_quran_ayah(surah,ayah,riwaya="hafs"):
    edition="quran-uthmani" if riwaya=="hafs" else "quran-warsh-muujawwad"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as s:
            async with s.get(f"{QURAN_API}/ayah/{surah}:{ayah}/{edition}") as r:
                data=await r.json()
                if data.get("status")=="OK": return data["data"]["text"]
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as s:
            async with s.get(f"{QURAN_API}/ayah/{surah}:{ayah}/quran-uthmani") as r:
                data=await r.json(); return data["data"]["text"]
    except: return "⚠️ تعذّر جلب الآية."

# ══════════════════════════════════════════════════════════════════
# UTILITY HELPERS
# ══════════════════════════════════════════════════════════════════
def banned_check(func):
    @wraps(func)
    async def wrapper(update:Update,context:ContextTypes.DEFAULT_TYPE):
        uid=update.effective_user.id if update.effective_user else None
        if uid and is_banned(uid): return
        return await func(update,context)
    return wrapper

async def safe_edit(query,text,reply_markup=None,parse_mode=ParseMode.MARKDOWN):
    try: await query.message.edit_text(text,parse_mode=parse_mode,reply_markup=reply_markup,disable_web_page_preview=True)
    except:
        try: await query.message.reply_text(text,parse_mode=parse_mode,reply_markup=reply_markup,disable_web_page_preview=True)
        except: pass

def btn_back(cb):  return InlineKeyboardButton("🔙 رجوع",      callback_data=cb)
def btn_cancel():  return InlineKeyboardButton("❌ إلغاء",      callback_data="cancel_state")
def btn_home():    return InlineKeyboardButton("🏠 الرئيسية",   callback_data="go_home")

def get_main_keyboard(uid=None):
    rows=[
        ["📖 القرآن الكريم",   "🌿 الورد اليومي"],
        ["📿 التسبيح",         "🌅 أذكار الصباح"],
        ["🌆 أذكار المساء",    "🌙 أذكار النوم"],
        ["🕌 أذكار الصلاة",   "🌺 أذكار الاستيقاظ"],
        ["💧 أذكار الوضوء",   "🌺 أدعية خاصة"],
        ["⭐ سنن يوم الجمعة", "🕐 أوقات الصلاة"],
        ["📅 التاريخ اليوم",  "📚 حديث اليوم"],
        ["🤲 دعاء اليوم",     "🎓 الدورات المجانية"],
        ["📊 إحصائياتي",      "🔔 إعدادات التنبيهات"],
        ["💬 استفسار",         "ℹ️ المساعدة"],
    ]
    if uid and is_admin(uid): rows.append(["⚙️ لوحة الإدارة"])
    return ReplyKeyboardMarkup(rows,resize_keyboard=True)

def build_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 إحصائيات",        callback_data="adm_stats"),
         InlineKeyboardButton("👥 المستخدمون",       callback_data="adm_users_list")],
        [InlineKeyboardButton("📋 استفسارات معلقة", callback_data="adm_inquiries"),
         InlineKeyboardButton("📜 كل الاستفسارات",  callback_data="adm_all_inquiries")],
        [InlineKeyboardButton("📚 الأحاديث",         callback_data="adm_manage_hadiths"),
         InlineKeyboardButton("🤲 الأدعية",          callback_data="adm_manage_duas")],
        [InlineKeyboardButton("📝 المحتوى",          callback_data="adm_manage_content"),
         InlineKeyboardButton("🔘 الأزرار الديناميكية", callback_data="dynbtn_root")],
        [InlineKeyboardButton("👤 إضافة مشرف",      callback_data="adm_add_admin"),
         InlineKeyboardButton("❌ حذف مشرف",         callback_data="adm_del_admin")],
        [InlineKeyboardButton("🚫 حظر مستخدم",      callback_data="adm_ban"),
         InlineKeyboardButton("✅ رفع الحظر",        callback_data="adm_unban")],
        [InlineKeyboardButton("📢 بث عام",           callback_data="adm_broadcast"),
         InlineKeyboardButton("📩 رسالة لمستخدم",   callback_data="adm_send_user")],
        [btn_home()],
    ])

def build_quran_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 رواية حفص",      callback_data="sp_0_hafs")],
        [InlineKeyboardButton("📖 رواية ورش",       callback_data="sp_0_warsh")],
        [InlineKeyboardButton("🎲 آية عشوائية",     callback_data="quran_random")],
        [btn_home()],
    ])

def build_surah_keyboard(page,riwaya,uid=None):
    surahs=list(SURAH_NAMES.items()); per=20; start=page*per; end=min(start+per,114)
    rows=[]; chunk=surahs[start:end]
    for i in range(0,len(chunk),3):
        rows.append([InlineKeyboardButton(f"{num}. {name}",callback_data=f"ss_{num}_{riwaya}") for num,name in chunk[i:i+3]])
    nav=[]
    if page>0:  nav.append(InlineKeyboardButton("◀️ السابق",callback_data=f"sp_{page-1}_{riwaya}"))
    if end<114: nav.append(InlineKeyboardButton("التالي ▶️",callback_data=f"sp_{page+1}_{riwaya}"))
    if nav: rows.append(nav)
    rows.append([btn_back("quran_menu"),btn_home()])
    return InlineKeyboardMarkup(rows)

def build_city_keyboard():
    rows=[]
    for i in range(0,len(ALGERIAN_CITIES),2):
        row=[InlineKeyboardButton(ALGERIAN_CITIES[i],callback_data=f"city_{ALGERIAN_CITIES[i]}")]
        if i+1<len(ALGERIAN_CITIES): row.append(InlineKeyboardButton(ALGERIAN_CITIES[i+1],callback_data=f"city_{ALGERIAN_CITIES[i+1]}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("✏️ مدينة أخرى (كتابة يدوية)",callback_data="city_other")])
    rows.append([btn_home()])
    return InlineKeyboardMarkup(rows)

# ══════════════════════════════════════════════════════════════════
# ADHKAR VIEW BUILDER
# ══════════════════════════════════════════════════════════════════
def build_adhkar_view(key,idx,counter,uid=None):
    title,lst=ADHKAR_MAP[key]; total=len(lst)
    if idx>=total: idx=total-1
    text_a,source,times=lst[idx]
    needs_counter=(times>1)
    nav=[]
    if idx>0:       nav.append(InlineKeyboardButton("◀️ السابق",callback_data=f"adhk_{key}_{idx-1}_0"))
    if idx<total-1: nav.append(InlineKeyboardButton("التالي ▶️",callback_data=f"adhk_{key}_{idx+1}_0"))
    rows=[]
    if needs_counter:
        done=(counter>=times)
        if done:
            rows.append([InlineKeyboardButton(f"✅ مكتمل ({times}/{times})",callback_data="noop")])
        else:
            rows.append([InlineKeyboardButton(f"📿 عدّ — {counter}/{times}",callback_data=f"adhk_count_{key}_{idx}_{counter}")])
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton("🔄 إعادة من البداية",callback_data=f"adhk_reset_{key}")])
    rows.append([btn_home()])
    # Admin controls per adhkar item
    if uid and is_admin(uid):
        rows.append([
            InlineKeyboardButton("✏️ تعديل النص",   callback_data=f"adm_adhk_edit_{key}_{idx}"),
            InlineKeyboardButton("🗑 حذف الذكر",    callback_data=f"adm_adhk_del_{key}_{idx}"),
        ])
        rows.append([InlineKeyboardButton("➕ إضافة ذكر جديد",callback_data=f"adm_adhk_add_{key}")])
    prog="✅" if (not needs_counter or counter>=times) else f"({counter}/{times})"
    msg=(f"*{title}*\n\n📿 الذكر *{idx+1}* من *{total}*\n\n{text_a}\n\n🔢 _{source}_\nالتكرار: {prog}")
    return msg,InlineKeyboardMarkup(rows)

# ══════════════════════════════════════════════════════════════════
# DYNAMIC BUTTONS RENDERER  ← THE CORE NEW SYSTEM
# ══════════════════════════════════════════════════════════════════
def render_dynbtn_page(parent_id, section, uid=None, back_cb="adm_panel"):
    """
    Renders a dynamic button page.
    - parent_id=None  → root level buttons for this section
    - parent_id=int   → children of that button
    Shows admin controls based on context:
      * Root: only ➕ Add (nothing to edit/delete yet at root level itself)
      * Inside a button: ➕ Add child | ✏️ Edit this btn | 🗑 Delete this btn
    """
    children = db_get_children(parent_id, section)
    rows = []

    # Show children as buttons
    for c in children:
        cid, clabel, ctype, ccontent = c
        icon = "📁" if ctype == "list" else "🔗" if ctype == "url" else "📝"
        rows.append([InlineKeyboardButton(f"{icon} {clabel}", callback_data=f"dynbtn_view_{cid}")])

    rows.append([btn_back(back_cb), btn_home()])

    # Admin controls — always visible to admin
    if uid and is_admin(uid):
        adm_row = [InlineKeyboardButton("➕ إضافة زر/نص", callback_data=f"dynbtn_add_{section}_{parent_id or 'root'}")]
        if parent_id is not None:
            adm_row.append(InlineKeyboardButton("✏️ تعديل هذا الزر", callback_data=f"dynbtn_edit_{parent_id}"))
            adm_row.append(InlineKeyboardButton("🗑 حذف هذا الزر",   callback_data=f"dynbtn_del_{parent_id}"))
        rows.append(adm_row)

        if children:
            rows.append([InlineKeyboardButton("🗑 حذف زر فرعي", callback_data=f"dynbtn_delchild_{section}_{parent_id or 'root'}")])

    return InlineKeyboardMarkup(rows)

def render_dynbtn_content(btn_row, uid=None):
    """
    Renders the content view of a single dynamic button.
    btn_row = (id, parent_id, section, label, type, content)
    """
    bid, parent_id, section, label, btn_type, content = btn_row
    back_cb = f"dynbtn_view_{parent_id}" if parent_id else f"dynbtn_root"

    if btn_type == "list":
        kb = render_dynbtn_page(bid, section, uid, back_cb=back_cb)
        return f"📁 *{label}*\nاختر:", kb

    elif btn_type == "url":
        rows = [
            [InlineKeyboardButton("🔗 افتح الرابط", url=content)],
            [btn_back(back_cb), btn_home()],
        ]
        if uid and is_admin(uid):
            rows.append([
                InlineKeyboardButton("✏️ تعديل الاسم",    callback_data=f"dynbtn_edit_{bid}"),
                InlineKeyboardButton("✏️ تعديل الرابط",   callback_data=f"dynbtn_editcontent_{bid}"),
                InlineKeyboardButton("🗑 حذف",             callback_data=f"dynbtn_del_{bid}"),
            ])
        return f"🔗 *{label}*\n\n{content}", InlineKeyboardMarkup(rows)

    else:  # text
        rows = [[btn_back(back_cb), btn_home()]]
        if uid and is_admin(uid):
            rows.append([
                InlineKeyboardButton("✏️ تعديل الاسم",    callback_data=f"dynbtn_edit_{bid}"),
                InlineKeyboardButton("✏️ تعديل المحتوى",  callback_data=f"dynbtn_editcontent_{bid}"),
                InlineKeyboardButton("🗑 حذف",             callback_data=f"dynbtn_del_{bid}"),
            ])
        return f"📝 *{label}*\n\n{content}", InlineKeyboardMarkup(rows)

# ══════════════════════════════════════════════════════════════════
# COMMANDS
# ══════════════════════════════════════════════════════════════════
@banned_check
async def cmd_start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    u=update.effective_user
    upsert_user(u.id,u.username,u.first_name,u.last_name)
    log_activity(u.id,"start"); context.user_data.clear()
    await update.message.reply_text(
        f"بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ\n\n"
        f"السلام عليكم ورحمة الله وبركاته 🌙\n\n"
        f"أهلاً وسهلاً *{u.first_name}* في *بوت المسلم الشامل* 🕌\n\n"
        f"هذا البوت رفيقك اليومي في:\n"
        f"📖 تلاوة القرآن الكريم ومتابعة ختمتك\n"
        f"📿 التسبيح والأذكار الصباحية والمسائية\n"
        f"🕐 أوقات الصلاة لمدينتك\n"
        f"🌿 الورد اليومي والأدعية المأثورة\n\n"
        f"_﴿وَالذَّاكِرِينَ اللَّهَ كَثِيرًا وَالذَّاكِرَاتِ أَعَدَّ اللَّهُ لَهُمْ مَغْفِرَةً وَأَجْرًا عَظِيمًا﴾_\n\n"
        f"اختر من القائمة أدناه 👇",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(u.id)
    )

@banned_check
async def cmd_help(update:Update,context:ContextTypes.DEFAULT_TYPE):
    u=update.effective_user; upsert_user(u.id,u.username,u.first_name,u.last_name); context.user_data.clear()
    await update.message.reply_text(
        "ℹ️ *دليل الاستخدام*\n\n"
        "📖 *القرآن* — تصفح برواية حفص أو ورش مع اختيار الآية\n"
        "🌿 *الورد* — تتبع ختمتك آية بآية\n"
        "📿 *التسبيح* — اختر تسبيحة وابدأ العد التفاعلي\n"
        "🌅 *أذكار الصباح/المساء* — مع عداد للأذكار المتكررة\n"
        "🕌 *أذكار الصلاة* — لكل ركن ذكره\n"
        "🕐 *أوقات الصلاة* — اضغط مدينتك مباشرة\n"
        "🔔 *التنبيهات* — تحكم في إشعاراتك اليومية\n"
        "💬 *استفسار* — تواصل مع الإدارة مباشرة\n\n"
        "للعودة للقائمة الرئيسية: /start",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(u.id)
    )

# ══════════════════════════════════════════════════════════════════
# MESSAGE HANDLER
# ══════════════════════════════════════════════════════════════════
@banned_check
async def handle_message(update:Update,context:ContextTypes.DEFAULT_TYPE):
    u=update.effective_user; text=update.message.text.strip()
    upsert_user(u.id,u.username,u.first_name,u.last_name)
    state=context.user_data.get("state","")

    if text in ["❌ إلغاء","إلغاء","الغاء","cancel"]:
        context.user_data.clear()
        await update.message.reply_text("↩️ تم الإلغاء.",reply_markup=get_main_keyboard(u.id)); return

    # ── Admin states ───────────────────────────────────────────────
    if state=="await_hadith":
        parts=text.split("|",1)
        if len(parts)==2:
            con=sqlite3.connect(DB_PATH); con.execute("INSERT INTO hadiths(text,source,added_by) VALUES(?,?,?)",(parts[0].strip(),parts[1].strip(),u.id)); con.commit(); con.close()
            context.user_data.clear(); await update.message.reply_text("✅ تم إضافة الحديث.",reply_markup=get_main_keyboard(u.id))
        else: await update.message.reply_text("⚠️ الصيغة: نص الحديث | المصدر\n\nأو اكتب إلغاء")
        return

    if state=="await_dua":
        parts=text.split("|",1)
        if len(parts)==2:
            con=sqlite3.connect(DB_PATH); con.execute("INSERT INTO duas(text,source,added_by) VALUES(?,?,?)",(parts[0].strip(),parts[1].strip(),u.id)); con.commit(); con.close()
            context.user_data.clear(); await update.message.reply_text("✅ تم إضافة الدعاء.",reply_markup=get_main_keyboard(u.id))
        else: await update.message.reply_text("⚠️ الصيغة: نص الدعاء | المصدر")
        return

    if state=="await_content":
        parts=text.split("|",2)
        if len(parts)==3:
            con=sqlite3.connect(DB_PATH); con.execute("INSERT INTO bot_content(category,text,source,added_by) VALUES(?,?,?,?)",(parts[0].strip(),parts[1].strip(),parts[2].strip(),u.id)); con.commit(); con.close()
            context.user_data.clear(); await update.message.reply_text("✅ تم إضافة المحتوى.",reply_markup=get_main_keyboard(u.id))
        else: await update.message.reply_text("⚠️ الصيغة: الفئة | النص | المصدر")
        return

    if state=="await_add_admin":
        try:
            nid=int(text.strip()); con=sqlite3.connect(DB_PATH)
            con.execute("INSERT INTO users(user_id,username,first_name,is_admin) VALUES(?,?,?,1) ON CONFLICT(user_id) DO UPDATE SET is_admin=1",(nid,"","مشرف"))
            con.commit(); con.close(); context.user_data.clear()
            await update.message.reply_text(f"✅ تم تعيين {nid} مشرفاً.",reply_markup=get_main_keyboard(u.id))
        except ValueError: await update.message.reply_text("⚠️ أرسل معرف رقمي.")
        return

    if state=="await_del_admin":
        try:
            did=int(text.strip())
            if did in SUPER_ADMINS: await update.message.reply_text("⚠️ لا يمكن حذف المشرف الرئيسي.")
            else:
                con=sqlite3.connect(DB_PATH); con.execute("UPDATE users SET is_admin=0 WHERE user_id=?",(did,)); con.commit(); con.close()
                context.user_data.clear(); await update.message.reply_text(f"✅ تم إزالة {did}.",reply_markup=get_main_keyboard(u.id))
        except ValueError: await update.message.reply_text("⚠️ أرسل معرف رقمي.")
        return

    if state=="await_ban":
        try:
            bid2=int(text.strip())
            if bid2 in SUPER_ADMINS: await update.message.reply_text("⚠️ لا يمكن حظر مشرف رئيسي.")
            else: ban_user(bid2); context.user_data.clear(); await update.message.reply_text(f"✅ تم حظر {bid2}.",reply_markup=get_main_keyboard(u.id))
        except ValueError: await update.message.reply_text("⚠️ أرسل معرف رقمي.")
        return

    if state=="await_unban":
        try:
            uid2=int(text.strip()); unban_user(uid2); context.user_data.clear()
            await update.message.reply_text(f"✅ تم رفع الحظر عن {uid2}.",reply_markup=get_main_keyboard(u.id))
        except ValueError: await update.message.reply_text("⚠️ أرسل معرف رقمي.")
        return

    if state=="await_broadcast":
        sent=0
        for xid in get_all_users():
            try: await context.bot.send_message(xid,text); sent+=1
            except: pass
        context.user_data.clear()
        await update.message.reply_text(f"✅ تم الإرسال لـ {sent} مستخدم.",reply_markup=get_main_keyboard(u.id))
        return

    if state=="await_send_user_id":
        try:
            tid=int(text.strip()); context.user_data["send_target"]=tid; context.user_data["state"]="await_send_user"
            await update.message.reply_text(f"✏️ أرسل الرسالة لـ {tid}:",reply_markup=ReplyKeyboardMarkup([["❌ إلغاء"]],resize_keyboard=True))
        except ValueError: await update.message.reply_text("⚠️ أرسل معرف رقمي.")
        return

    if state=="await_send_user":
        tid=context.user_data.get("send_target")
        if tid:
            try:
                await context.bot.send_message(tid,text); context.user_data.clear()
                await update.message.reply_text("✅ تم الإرسال.",reply_markup=get_main_keyboard(u.id))
            except Exception as e: await update.message.reply_text(f"⚠️ فشل: {e}")
        return

    if state=="await_inquiry":
        iid=save_inquiry(u.id,u.username,u.first_name,text); context.user_data.clear()
        await update.message.reply_text(
            f"✅ *تم استلام استفسارك بنجاح* 📩\n\n"
            f"رقم استفسارك: *#{iid}*\n"
            f"سيرد عليك أحد المشرفين في أقرب وقت إن شاء الله.\n\n"
            f"_جزاك الله خيراً على تواصلك معنا_ 🌟",
            parse_mode=ParseMode.MARKDOWN,reply_markup=get_main_keyboard(u.id))
        for aid in get_all_admins():
            try:
                await context.bot.send_message(aid,
                    f"📩 *استفسار جديد #{iid}*\n"
                    f"👤 {u.first_name} (@{u.username or '—'}) | `{u.id}`\n\n"
                    f"💬 {text}",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(f"↩️ رد على #{iid}",callback_data=f"adm_direct_reply_{iid}_{u.id}")
                    ]]))
            except: pass
        return

    if state=="await_reply_text":
        iid=context.user_data.get("reply_iid"); target=context.user_data.get("reply_target")
        if iid:
            reply_to_inquiry(iid,text)
            if target:
                try:
                    await context.bot.send_message(target,
                        f"📩 *رد الإدارة على استفسارك #{iid}:*\n\n{text}\n\n_بارك الله فيك_",
                        parse_mode=ParseMode.MARKDOWN)
                except: pass
            context.user_data.clear()
            await update.message.reply_text("✅ تم إرسال الرد للمستخدم.",reply_markup=get_main_keyboard(u.id))
        return

    if state=="await_city_manual":
        city=text.strip(); save_user_city(u.id,city); context.user_data.clear()
        pt=await fetch_prayer_times(city)
        await update.message.reply_text(pt,parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 تغيير المدينة",callback_data="prayer_change_city")],[btn_home()]]))
        return

    # ── Dynamic button admin states ────────────────────────────────
    if state=="dynbtn_await_label":
        context.user_data["dynbtn_new_label"]=text.strip()
        context.user_data["state"]="dynbtn_await_type"
        await update.message.reply_text(
            f"اسم الزر: *{text.strip()}*\n\nاختر نوع الزر:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 نص",         callback_data="dynbtn_type_text")],
                [InlineKeyboardButton("📁 قائمة أزرار",callback_data="dynbtn_type_list")],
                [InlineKeyboardButton("🔗 رابط",        callback_data="dynbtn_type_url")],
                [btn_cancel()],
            ]))
        return

    if state=="dynbtn_await_content":
        label   =context.user_data.get("dynbtn_new_label","زر جديد")
        btn_type=context.user_data.get("dynbtn_new_type","text")
        section =context.user_data.get("dynbtn_section","root")
        parent  =context.user_data.get("dynbtn_parent_id",None)
        db_add_btn(parent,section,label,btn_type,text.strip(),u.id)
        context.user_data.clear()
        await update.message.reply_text(
            f"✅ تم إضافة الزر *{label}* بنجاح!",
            parse_mode=ParseMode.MARKDOWN,reply_markup=get_main_keyboard(u.id))
        return

    if state=="dynbtn_await_edit_label":
        bid=context.user_data.get("dynbtn_edit_id")
        if bid:
            db_update_btn_label(bid,text.strip()); context.user_data.clear()
            await update.message.reply_text(f"✅ تم تعديل اسم الزر إلى: *{text.strip()}*",
                parse_mode=ParseMode.MARKDOWN,reply_markup=get_main_keyboard(u.id))
        return

    if state=="dynbtn_await_edit_content":
        bid=context.user_data.get("dynbtn_edit_id")
        if bid:
            db_update_btn_content(bid,text.strip()); context.user_data.clear()
            await update.message.reply_text("✅ تم تعديل محتوى الزر بنجاح.",reply_markup=get_main_keyboard(u.id))
        return

    # ── Adhkar admin states ────────────────────────────────────────
    if state=="adm_adhk_await_edit":
        key=context.user_data.get("adhk_key"); idx=context.user_data.get("adhk_idx",0)
        if key is not None and idx is not None:
            _,lst=ADHKAR_MAP[key]
            if 0<=idx<len(lst):
                lst[idx]=(text.strip(),lst[idx][1],lst[idx][2])
            context.user_data.clear()
            await update.message.reply_text("✅ تم تعديل نص الذكر.",reply_markup=get_main_keyboard(u.id))
        return

    if state=="adm_adhk_await_add":
        key=context.user_data.get("adhk_key")
        if key:
            _,lst=ADHKAR_MAP[key]
            parts=text.split("|")
            new_text=parts[0].strip()
            new_source=parts[1].strip() if len(parts)>1 else "—"
            new_times=int(parts[2].strip()) if len(parts)>2 and parts[2].strip().isdigit() else 1
            lst.append((new_text,new_source,new_times))
            context.user_data.clear()
            await update.message.reply_text("✅ تم إضافة الذكر الجديد.",reply_markup=get_main_keyboard(u.id))
        return

    # ── Main keyboard routing ──────────────────────────────────────
    log_activity(u.id,"menu",text); context.user_data.clear()

    if text=="📖 القرآن الكريم":
        await update.message.reply_text("📖 *القرآن الكريم*\nاختر الرواية:",
            parse_mode=ParseMode.MARKDOWN,reply_markup=build_quran_keyboard())

    elif text=="🌿 الورد اليومي":
        surah,ayah=get_wird_progress(u.id); sname=SURAH_NAMES.get(surah,str(surah)); total=SURAH_AYAH_COUNT.get(surah,1)
        await update.message.reply_text(
            f"🌿 *الورد اليومي*\n\nأنت في: *{sname}* — آية {ayah}/{total}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"▶️ متابعة — {sname} آية {ayah}",callback_data=f"wird_read_{surah}_{ayah}_hafs")],
                [InlineKeyboardButton("↩️ إعادة الورد من البداية",        callback_data="wird_reset")],
                [InlineKeyboardButton("🔄 تبديل رواية ورش",              callback_data=f"wird_read_{surah}_{ayah}_warsh")],
                [btn_home()],
            ]))

    elif text=="📿 التسبيح":
        rows=[[InlineKeyboardButton(f"📿 {TASBIH_LIST[i][0]}",callback_data=f"tsb_select_{i}")] for i in range(len(TASBIH_LIST))]
        rows.append([InlineKeyboardButton("📊 إحصائياتي",callback_data="tsb_stats"),btn_home()])
        await update.message.reply_text("📿 *اختر تسبيحة للبدء:*",parse_mode=ParseMode.MARKDOWN,reply_markup=InlineKeyboardMarkup(rows))

    elif text=="🌅 أذكار الصباح":
        idx,cnt=get_adhkar_progress(u.id,"morning"); msg,kb=build_adhkar_view("morning",idx,cnt,u.id)
        await update.message.reply_text(msg,parse_mode=ParseMode.MARKDOWN,reply_markup=kb)

    elif text=="🌆 أذكار المساء":
        idx,cnt=get_adhkar_progress(u.id,"evening"); msg,kb=build_adhkar_view("evening",idx,cnt,u.id)
        await update.message.reply_text(msg,parse_mode=ParseMode.MARKDOWN,reply_markup=kb)

    elif text=="🌙 أذكار النوم":
        idx,cnt=get_adhkar_progress(u.id,"sleep"); msg,kb=build_adhkar_view("sleep",idx,cnt,u.id)
        await update.message.reply_text(msg,parse_mode=ParseMode.MARKDOWN,reply_markup=kb)

    elif text=="🌺 أذكار الاستيقاظ":
        idx,cnt=get_adhkar_progress(u.id,"wakeup"); msg,kb=build_adhkar_view("wakeup",idx,cnt,u.id)
        await update.message.reply_text(msg,parse_mode=ParseMode.MARKDOWN,reply_markup=kb)

    elif text=="💧 أذكار الوضوء":
        idx,cnt=get_adhkar_progress(u.id,"wudu"); msg,kb=build_adhkar_view("wudu",idx,cnt,u.id)
        await update.message.reply_text(msg,parse_mode=ParseMode.MARKDOWN,reply_markup=kb)

    elif text=="🕌 أذكار الصلاة":
        keys=list(PRAYER_ADHKAR.keys())
        rows=[[InlineKeyboardButton(k,callback_data=f"pradh_{i}")] for i,k in enumerate(keys)]
        rows.append([btn_home()])
        await update.message.reply_text("🕌 *أذكار الصلاة*\nاختر القسم:",parse_mode=ParseMode.MARKDOWN,reply_markup=InlineKeyboardMarkup(rows))

    elif text=="🌺 أدعية خاصة":
        keys=list(SPECIAL_DUAS.keys())
        rows=[[InlineKeyboardButton(k,callback_data=f"sd_{i}")] for i,k in enumerate(keys)]
        rows.append([btn_home()])
        await update.message.reply_text("🌺 *أدعية خاصة*\nاختر:",parse_mode=ParseMode.MARKDOWN,reply_markup=InlineKeyboardMarkup(rows))

    elif text=="⭐ سنن يوم الجمعة":
        rows=[[InlineKeyboardButton(s["title"],callback_data=f"fri_{i}")] for i,s in enumerate(FRIDAY_SUNNAN)]
        rows.append([InlineKeyboardButton("📖 سور الجمعة",callback_data="fri_surahs")])
        rows.append([btn_home()])
        await update.message.reply_text("⭐ *سنن يوم الجمعة*\nاختر:",parse_mode=ParseMode.MARKDOWN,reply_markup=InlineKeyboardMarkup(rows))

    elif text=="🕐 أوقات الصلاة":
        city=get_user_city(u.id)
        if city:
            pt=await fetch_prayer_times(city)
            await update.message.reply_text(pt,parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 تغيير المدينة",callback_data="prayer_change_city")],[btn_home()]]))
        else:
            await update.message.reply_text("🏙️ *اختر مدينتك:*",parse_mode=ParseMode.MARKDOWN,reply_markup=build_city_keyboard())

    elif text=="📅 التاريخ اليوم":
        await update.message.reply_text(await fetch_dates(),parse_mode=ParseMode.MARKDOWN)

    elif text=="📚 حديث اليوم":
        row=get_random_hadith()
        if row: await update.message.reply_text(f"📚 *حديث اليوم*\n\n{row[0]}\n\n📖 _{row[1]}_",parse_mode=ParseMode.MARKDOWN)
        else:   await update.message.reply_text("⚠️ لا توجد أحاديث مضافة بعد.\n_سيضيف المشرف قريباً إن شاء الله_",parse_mode=ParseMode.MARKDOWN)

    elif text=="🤲 دعاء اليوم":
        row=get_random_dua()
        if row: await update.message.reply_text(f"🤲 *دعاء اليوم*\n\n{row[0]}\n\n📖 _{row[1]}_",parse_mode=ParseMode.MARKDOWN)
        else:   await update.message.reply_text("⚠️ لا توجد أدعية مضافة بعد.",parse_mode=ParseMode.MARKDOWN)

    elif text=="🎓 الدورات المجانية":
        kb=render_dynbtn_page(None,"courses",u.id,back_cb="go_home")
        children=db_get_children(None,"courses")
        msg="🎓 *الدورات المجانية*\nاختر:" if children else "⚠️ لا توجد دورات مضافة حالياً.\n_سيضيفها المشرف قريباً_"
        await update.message.reply_text(msg,parse_mode=ParseMode.MARKDOWN,reply_markup=kb)

    elif text=="📊 إحصائياتي":
        s=get_user_full_stats(u.id); sname=SURAH_NAMES.get(s["wird_surah"],str(s["wird_surah"]))
        await update.message.reply_text(
            f"📊 *إحصائياتك الشخصية*\n\n"
            f"📖 الورد: سورة *{sname}* آية {s['wird_ayah']}\n"
            f"📿 إجمالي التسبيح: *{s['total_t']}* مرة\n"
            f"📚 سور متابعة: *{s['surahs_done']}* سورة\n"
            f"💬 استفساراتك: *{s['inquiries']}*\n\n"
            f"_واصل! كل عمل صالح يُكتب لك إن شاء الله_ 🌟",
            parse_mode=ParseMode.MARKDOWN)

    elif text=="🔔 إعدادات التنبيهات":
        ns=get_notif_settings(u.id)
        rows=[
            [InlineKeyboardButton(f"{'✅' if ns['morning'] else '❌'} أذكار الصباح",callback_data="notif_toggle_morning"),
             InlineKeyboardButton(f"{'✅' if ns['evening'] else '❌'} أذكار المساء",callback_data="notif_toggle_evening")],
            [InlineKeyboardButton(f"{'✅' if ns['wird'] else '❌'} تنبيه الورد",    callback_data="notif_toggle_wird"),
             InlineKeyboardButton(f"{'✅' if ns['friday'] else '❌'} تنبيه الجمعة", callback_data="notif_toggle_friday")],
            [btn_home()],
        ]
        await update.message.reply_text("🔔 *إعدادات التنبيهات*\nاضغط لتفعيل/إيقاف:",parse_mode=ParseMode.MARKDOWN,reply_markup=InlineKeyboardMarkup(rows))

    elif text=="💬 استفسار":
        context.user_data["state"]="await_inquiry"
        await update.message.reply_text(
            "💬 *أرسل استفسارك*\n\n"
            "اكتب سؤالك أو ملاحظتك وسيصلك الرد من الإدارة مباشرة 📩\n\n"
            "_اضغط ❌ إلغاء للخروج_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ReplyKeyboardMarkup([["❌ إلغاء"]],resize_keyboard=True))

    elif text=="ℹ️ المساعدة":
        await cmd_help(update,context)

    elif text=="⚙️ لوحة الإدارة":
        if not is_admin(u.id): await update.message.reply_text("⛔ ليس لديك صلاحية الوصول."); return
        stats=get_admin_stats()
        await update.message.reply_text(
            f"⚙️ *لوحة الإدارة*\n\n"
            f"👥 المستخدمون: *{stats['users']}* | 🛡 المشرفون: *{stats['admins']}*\n"
            f"🚫 المحظورون: *{stats['banned']}* | ✅ نشطون اليوم: *{stats['active_today']}*\n"
            f"📚 الأحاديث: *{stats['hadiths']}* | 🤲 الأدعية: *{stats['duas']}*\n"
            f"📿 إجمالي التسبيح: *{stats['tasbih_total']}*\n"
            f"🔘 الأزرار الديناميكية: *{stats['dyn_buttons']}*\n"
            f"📋 معلق: *{stats['pending']}* | ✅ مُجاب: *{stats['replied']}*",
            parse_mode=ParseMode.MARKDOWN,reply_markup=build_admin_keyboard())
    else:
        await update.message.reply_text("اضغط /start للقائمة الرئيسية.")

# ══════════════════════════════════════════════════════════════════
# CALLBACK HANDLER
# ══════════════════════════════════════════════════════════════════
@banned_check
async def handle_callback(update:Update,context:ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer()
    data=query.data; u=query.from_user; uid=u.id

    # ── Universal ──────────────────────────────────────────────────
    if data=="cancel_state":
        context.user_data.clear()
        await safe_edit(query,"↩️ تم الإلغاء.",reply_markup=InlineKeyboardMarkup([[btn_home()]])); return

    if data=="go_home":
        context.user_data.clear()
        await safe_edit(query,"🏠 *القائمة الرئيسية*\n\nاختر من أزرار الكيبورد أدناه 👇",reply_markup=InlineKeyboardMarkup([[btn_home()]])); return

    if data=="noop": return

    # ── Notif toggles ──────────────────────────────────────────────
    if data.startswith("notif_toggle_"):
        key=data.replace("notif_toggle_",""); ns=get_notif_settings(uid)
        set_notif_setting(uid,key,0 if ns.get(key,1) else 1); ns=get_notif_settings(uid)
        rows=[
            [InlineKeyboardButton(f"{'✅' if ns['morning'] else '❌'} أذكار الصباح",callback_data="notif_toggle_morning"),
             InlineKeyboardButton(f"{'✅' if ns['evening'] else '❌'} أذكار المساء",callback_data="notif_toggle_evening")],
            [InlineKeyboardButton(f"{'✅' if ns['wird'] else '❌'} تنبيه الورد",    callback_data="notif_toggle_wird"),
             InlineKeyboardButton(f"{'✅' if ns['friday'] else '❌'} تنبيه الجمعة", callback_data="notif_toggle_friday")],
            [btn_home()],
        ]
        await safe_edit(query,"🔔 *إعدادات التنبيهات*\nاضغط لتفعيل/إيقاف:",reply_markup=InlineKeyboardMarkup(rows)); return

    # ── Quran ──────────────────────────────────────────────────────
    if data=="quran_menu":
        await safe_edit(query,"📖 *القرآن الكريم*\nاختر الرواية:",reply_markup=build_quran_keyboard()); return

    if data=="quran_random":
        s=random.randint(1,114); a=random.randint(1,SURAH_AYAH_COUNT[s])
        txt=await fetch_quran_ayah(s,a)
        await safe_edit(query,f"📖 *{SURAH_NAMES[s]}* — آية {a}\n\n{txt}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎲 آية أخرى",callback_data="quran_random")],
                [btn_back("quran_menu"),btn_home()],
            ])); return

    if data.startswith("sp_"):
        parts=data.split("_",2); page=int(parts[1]); riwaya=parts[2]
        rname="حفص" if riwaya=="hafs" else "ورش"
        await safe_edit(query,f"📖 اختر السورة — رواية {rname}:",reply_markup=build_surah_keyboard(page,riwaya,uid)); return

    if data.startswith("ss_"):
        parts=data.split("_",2); surah=int(parts[1]); riwaya=parts[2]
        last=get_surah_progress(uid,surah,riwaya); total=SURAH_AYAH_COUNT[surah]; rname="حفص" if riwaya=="hafs" else "ورش"
        rows=[
            [InlineKeyboardButton("▶️ ابدأ من البداية",       callback_data=f"sq_{surah}_1_{riwaya}")],
            [InlineKeyboardButton(f"📍 متابعة من آية {last}", callback_data=f"sq_{surah}_{last}_{riwaya}")],
            [InlineKeyboardButton("🔢 اختر آية للبدء منها",   callback_data=f"sq_choose_{surah}_{riwaya}")],
            [btn_back(f"sp_0_{riwaya}"),btn_home()],
        ]
        await safe_edit(query,f"📖 *{SURAH_NAMES[surah]}*\nعدد الآيات: {total} | رواية {rname}\nآخر موضع: آية {last}",
            reply_markup=InlineKeyboardMarkup(rows)); return

    if data.startswith("sq_choose_") and not data.startswith("sq_choosep_"):
        parts=data.split("_"); surah=int(parts[2]); riwaya=parts[3]
        total=SURAH_AYAH_COUNT[surah]
        rows=[]
        for a in range(1,min(21,total+1)):
            if (a-1)%5==0: rows.append([])
            rows[-1].append(InlineKeyboardButton(str(a),callback_data=f"sq_{surah}_{a}_{riwaya}"))
        if total>20: rows.append([InlineKeyboardButton("التالي ▶️",callback_data=f"sq_choosep_{surah}_20_{riwaya}")])
        rows.append([btn_back(f"ss_{surah}_{riwaya}"),btn_home()])
        await safe_edit(query,f"🔢 اختر رقم الآية — *{SURAH_NAMES[surah]}* ({total} آية):",reply_markup=InlineKeyboardMarkup(rows)); return

    if data.startswith("sq_choosep_"):
        parts=data.split("_"); surah=int(parts[2]); start=int(parts[3]); riwaya=parts[4]
        total=SURAH_AYAH_COUNT[surah]
        rows=[]
        for a in range(start+1,min(start+21,total+1)):
            if (a-start-1)%5==0: rows.append([])
            rows[-1].append(InlineKeyboardButton(str(a),callback_data=f"sq_{surah}_{a}_{riwaya}"))
        nav=[]
        if start>0:         nav.append(InlineKeyboardButton("◀️ السابق",callback_data=f"sq_choosep_{surah}_{max(0,start-20)}_{riwaya}"))
        if start+20<total:  nav.append(InlineKeyboardButton("التالي ▶️",callback_data=f"sq_choosep_{surah}_{start+20}_{riwaya}"))
        if nav: rows.append(nav)
        rows.append([btn_back(f"ss_{surah}_{riwaya}"),btn_home()])
        await safe_edit(query,f"🔢 اختر رقم الآية — *{SURAH_NAMES[surah]}* ({total} آية):",reply_markup=InlineKeyboardMarkup(rows)); return

    if data.startswith("sq_") and not data.startswith("sq_choose"):
        parts=data.split("_",3); surah=int(parts[1]); ayah=int(parts[2]); riwaya=parts[3]
        total=SURAH_AYAH_COUNT[surah]
        txt=await fetch_quran_ayah(surah,ayah,riwaya); save_surah_progress(uid,surah,ayah,riwaya)
        nav=[]
        if ayah>1:    nav.append(InlineKeyboardButton("◀️ السابقة",callback_data=f"sq_{surah}_{ayah-1}_{riwaya}"))
        if ayah<total:nav.append(InlineKeyboardButton("التالية ▶️",callback_data=f"sq_{surah}_{ayah+1}_{riwaya}"))
        rows=[]; 
        if nav: rows.append(nav)
        if ayah==total and surah<114:
            rows.append([InlineKeyboardButton(f"▶️ السورة التالية: {SURAH_NAMES[surah+1]}",callback_data=f"ss_{surah+1}_{riwaya}")])
        rows.append([btn_back(f"ss_{surah}_{riwaya}"),btn_home()])
        rname="حفص" if riwaya=="hafs" else "ورش"
        await safe_edit(query,f"📖 *{SURAH_NAMES[surah]}* — آية {ayah}/{total} ({rname})\n\n{txt}",reply_markup=InlineKeyboardMarkup(rows)); return

    # ── Wird ───────────────────────────────────────────────────────
    if data.startswith("wird_read_"):
        parts=data.split("_"); surah=int(parts[2]); ayah=int(parts[3]); riwaya=parts[4]
        total=SURAH_AYAH_COUNT[surah]; txt=await fetch_quran_ayah(surah,ayah,riwaya); save_wird_progress(uid,surah,ayah)
        nav=[]
        if ayah>1:    nav.append(InlineKeyboardButton("◀️ السابقة",callback_data=f"wird_read_{surah}_{ayah-1}_{riwaya}"))
        if ayah<total:nav.append(InlineKeyboardButton("التالية ▶️",callback_data=f"wird_read_{surah}_{ayah+1}_{riwaya}"))
        rows=[]
        if nav: rows.append(nav)
        if ayah==total and surah<114:
            rows.append([InlineKeyboardButton(f"▶️ سورة {SURAH_NAMES[surah+1]}",callback_data=f"wird_read_{surah+1}_1_{riwaya}")])
        rows.append([btn_home()])
        rname="حفص" if riwaya=="hafs" else "ورش"
        await safe_edit(query,f"🌿 *الورد — {SURAH_NAMES[surah]}* آية {ayah}/{total} ({rname})\n\n{txt}",reply_markup=InlineKeyboardMarkup(rows)); return

    if data=="wird_reset":
        save_wird_progress(uid,2,1)
        await safe_edit(query,"✅ تمت إعادة الورد من البداية — سورة البقرة آية 1.",reply_markup=InlineKeyboardMarkup([[btn_home()]])); return

    # ── Tasbih ─────────────────────────────────────────────────────
    if data=="tsb_menu":
        rows=[[InlineKeyboardButton(f"📿 {TASBIH_LIST[i][0]}",callback_data=f"tsb_select_{i}")] for i in range(len(TASBIH_LIST))]
        rows.append([InlineKeyboardButton("📊 إحصائياتي",callback_data="tsb_stats"),btn_home()])
        await safe_edit(query,"📿 *اختر تسبيحة للبدء:*",reply_markup=InlineKeyboardMarkup(rows)); return

    if data.startswith("tsb_select_"):
        pidx=int(data.split("_")[2])
        if pidx>=len(TASBIH_LIST): pidx=0
        phrase,fadl,target=TASBIH_LIST[pidx]; save_tasbih_session(uid,pidx,0)
        await safe_edit(query,
            f"📿 *{phrase}*\n\n💡 {fadl}\n\n🎯 الهدف: *{target}* مرة\n\nاضغط الزر للبدء:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"📿 ابدأ العد (0/{target})",callback_data=f"tsb_tap_{pidx}_0")],
                [btn_back("tsb_menu"),btn_home()],
            ])); return

    if data.startswith("tsb_tap_"):
        parts=data.split("_"); pidx=int(parts[2]); count=int(parts[3])+1
        if pidx>=len(TASBIH_LIST): pidx=0
        phrase,fadl,target=TASBIH_LIST[pidx]; save_tasbih_session(uid,pidx,count)
        if count>=target:
            log_tasbih(uid,phrase,count); mot=random.choice(MOTIVATION_MSGS)
            await safe_edit(query,
                f"✅ *أتممت التسبيحة بحمد الله!*\n\n📿 *{phrase}*\n\n{mot}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 إعادة نفس التسبيحة",callback_data=f"tsb_select_{pidx}")],
                    [btn_back("tsb_menu"),btn_home()],
                ]))
        else:
            prog=int((count/target)*10); bar="▓"*prog+"░"*(10-prog)
            await safe_edit(query,
                f"📿 *{phrase}*\n\n💡 {fadl}\n\n{bar}\n*{count} / {target}*",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"📿 سبّح  ({count}/{target})",callback_data=f"tsb_tap_{pidx}_{count}")],
                    [InlineKeyboardButton("🔄 إعادة",callback_data=f"tsb_select_{pidx}"),
                     InlineKeyboardButton("📊 إحصاء",callback_data="tsb_stats")],
                    [btn_back("tsb_menu"),btn_home()],
                ]))
        return

    if data=="tsb_stats":
        total,rows_s=get_tasbih_stats(uid)
        lines="\n".join([f"• {r[0][:35]}: *{r[1]}*" for r in rows_s]) if rows_s else "لا توجد إحصائيات بعد."
        await safe_edit(query,f"📊 *إحصائيات التسبيح*\n\nالإجمالي: *{total}*\n\n{lines}",
            reply_markup=InlineKeyboardMarkup([[btn_back("tsb_menu"),btn_home()]])); return

    # ── Adhkar ─────────────────────────────────────────────────────
    if data.startswith("adhk_count_"):
        parts=data.split("_",4); key=parts[2]; idx=int(parts[3]); counter=int(parts[4])+1
        save_adhkar_progress(uid,key,idx,counter); msg,kb=build_adhkar_view(key,idx,counter,uid)
        await safe_edit(query,msg,reply_markup=kb); return

    if data.startswith("adhk_reset_"):
        key=data[len("adhk_reset_"):]; save_adhkar_progress(uid,key,0,0)
        msg,kb=build_adhkar_view(key,0,0,uid); await safe_edit(query,msg,reply_markup=kb); return

    if data.startswith("adhk_"):
        parts=data.split("_",3); key=parts[1]; idx=int(parts[2]); counter=int(parts[3]) if len(parts)>3 else 0
        msg,kb=build_adhkar_view(key,idx,counter,uid); await safe_edit(query,msg,reply_markup=kb); return

    # ── Adhkar Admin Controls ──────────────────────────────────────
    if data.startswith("adm_adhk_edit_"):
        if not is_admin(uid): await query.answer("⛔"); return
        parts=data.split("_",4); key=parts[3]; idx=int(parts[4])
        _,lst=ADHKAR_MAP.get(key,("—",[]))
        if 0<=idx<len(lst):
            context.user_data["state"]="adm_adhk_await_edit"
            context.user_data["adhk_key"]=key; context.user_data["adhk_idx"]=idx
            await safe_edit(query,
                f"✏️ *تعديل الذكر {idx+1}*\n\nالنص الحالي:\n_{lst[idx][0][:100]}_\n\nأرسل النص الجديد:",
                reply_markup=InlineKeyboardMarkup([[btn_cancel()]]))
        return

    if data.startswith("adm_adhk_del_"):
        if not is_admin(uid): await query.answer("⛔"); return
        parts=data.split("_",4); key=parts[3]; idx=int(parts[4])
        _,lst=ADHKAR_MAP.get(key,("—",[]))
        if 0<=idx<len(lst) and len(lst)>1:
            del lst[idx]
            await safe_edit(query,f"✅ تم حذف الذكر.",
                reply_markup=InlineKeyboardMarkup([[btn_back(f"adhk_{key}_0_0"),btn_home()]]))
        else:
            await safe_edit(query,"⚠️ لا يمكن حذف الذكر الوحيد.",
                reply_markup=InlineKeyboardMarkup([[btn_home()]]))
        return

    if data.startswith("adm_adhk_add_"):
        if not is_admin(uid): await query.answer("⛔"); return
        key=data[len("adm_adhk_add_"):]
        context.user_data["state"]="adm_adhk_await_add"; context.user_data["adhk_key"]=key
        await safe_edit(query,
            f"➕ *إضافة ذكر جديد*\n\nالصيغة:\n`نص الذكر | المصدر | عدد التكرار`\n\nمثال:\n`سبحان الله | رواه مسلم | 33`",
            reply_markup=InlineKeyboardMarkup([[btn_cancel()]]))
        return

    # ── Prayer Adhkar ──────────────────────────────────────────────
    if data.startswith("pradh_"):
        idx=int(data.split("_")[1]); keys=list(PRAYER_ADHKAR.keys())
        if idx>=len(keys): return
        items=PRAYER_ADHKAR[keys[idx]]
        lines="\n\n".join([f"*{i+1}.* {it[0]}\n🔢 _{it[1]}_" for i,it in enumerate(items)])
        await safe_edit(query,f"🕌 *{keys[idx]}*\n\n{lines}",
            reply_markup=InlineKeyboardMarkup([[btn_back("prayer_adhkar_back"),btn_home()]])); return

    if data=="prayer_adhkar_back":
        keys=list(PRAYER_ADHKAR.keys())
        rows=[[InlineKeyboardButton(k,callback_data=f"pradh_{i}")] for i,k in enumerate(keys)]
        rows.append([btn_home()])
        await safe_edit(query,"🕌 *أذكار الصلاة*\nاختر القسم:",reply_markup=InlineKeyboardMarkup(rows)); return

    # ── Special Duas ───────────────────────────────────────────────
    if data.startswith("sd_"):
        idx=int(data.split("_")[1]); keys=list(SPECIAL_DUAS.keys())
        if idx>=len(keys): return
        items=SPECIAL_DUAS[keys[idx]]
        lines="\n\n".join([f"*{i+1}.* {it[0]}\n🔢 _{it[1]}_" for i,it in enumerate(items)])
        await safe_edit(query,f"🌺 *{keys[idx]}*\n\n{lines}",
            reply_markup=InlineKeyboardMarkup([[btn_back("sd_back"),btn_home()]])); return

    if data=="sd_back":
        keys=list(SPECIAL_DUAS.keys())
        rows=[[InlineKeyboardButton(k,callback_data=f"sd_{i}")] for i,k in enumerate(keys)]
        rows.append([btn_home()])
        await safe_edit(query,"🌺 *أدعية خاصة*\nاختر:",reply_markup=InlineKeyboardMarkup(rows)); return

    # ── Friday ─────────────────────────────────────────────────────
    if data.startswith("fri_") and data!="fri_surahs":
        try: idx=int(data.split("_")[1])
        except: return
        if idx>=len(FRIDAY_SUNNAN): return
        s=FRIDAY_SUNNAN[idx]
        await safe_edit(query,f"⭐ *{s['title']}*\n\n{s['text']}\n\n📖 _{s['source']}_",
            reply_markup=InlineKeyboardMarkup([[btn_back("fri_back"),btn_home()]])); return

    if data=="fri_surahs":
        lines="\n\n".join([f"*{SURAH_NAMES[n]}*\n{d}" for n,d in FRIDAY_SURAHS.items()])
        await safe_edit(query,f"📖 *سور يوم الجمعة*\n\n{lines}",
            reply_markup=InlineKeyboardMarkup([[btn_back("fri_back"),btn_home()]])); return

    if data=="fri_back":
        rows=[[InlineKeyboardButton(s["title"],callback_data=f"fri_{i}")] for i,s in enumerate(FRIDAY_SUNNAN)]
        rows.append([InlineKeyboardButton("📖 سور الجمعة",callback_data="fri_surahs"),btn_home()])
        await safe_edit(query,"⭐ *سنن يوم الجمعة*\nاختر:",reply_markup=InlineKeyboardMarkup(rows)); return

    # ── Prayer times / city ────────────────────────────────────────
    if data=="prayer_change_city":
        await safe_edit(query,"🏙️ *اختر مدينتك:*",reply_markup=build_city_keyboard()); return

    if data.startswith("city_"):
        city=data[5:]
        if city=="other":
            context.user_data["state"]="await_city_manual"
            await safe_edit(query,"✏️ أرسل اسم مدينتك بالإنجليزية (مثال: Algiers):",
                reply_markup=InlineKeyboardMarkup([[btn_cancel()]])); return
        save_user_city(uid,city); pt=await fetch_prayer_times(city)
        await safe_edit(query,pt,reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 تغيير المدينة",callback_data="prayer_change_city")],[btn_home()]])); return

    # ══════════════════════════════════════════════════════════════
    # DYNAMIC BUTTONS SYSTEM
    # ══════════════════════════════════════════════════════════════

    # Root level
    if data=="dynbtn_root":
        kb=render_dynbtn_page(None,"root",uid,back_cb="adm_panel")
        children=db_get_children(None,"root")
        msg="🔘 *الأزرار الديناميكية — الرئيسية*\nاختر:" if children else "🔘 *الأزرار الديناميكية*\n\nلا توجد أزرار بعد. اضغط ➕ لإضافة الأول."
        await safe_edit(query,msg,reply_markup=kb); return

    # View a button (navigate into it)
    if data.startswith("dynbtn_view_"):
        bid=int(data.split("_")[2]); btn_row=db_get_btn(bid)
        if not btn_row: await query.answer("⚠️ الزر غير موجود."); return
        msg,kb=render_dynbtn_content(btn_row,uid)
        await safe_edit(query,msg,reply_markup=kb); return

    # ADD button — dynbtn_add_SECTION_PARENTID(or 'root')
    if data.startswith("dynbtn_add_"):
        if not is_admin(uid): await query.answer("⛔"); return
        parts=data.split("_",3); section=parts[2]; parent_raw=parts[3]
        parent_id=None if parent_raw=="root" else int(parent_raw)
        context.user_data["state"]="dynbtn_await_label"
        context.user_data["dynbtn_section"]=section
        context.user_data["dynbtn_parent_id"]=parent_id
        await safe_edit(query,
            f"➕ *إضافة زر جديد*\n\nالقسم: *{section}* | الأب: {'رئيسي' if parent_id is None else f'#{parent_id}'}\n\n✏️ أرسل *اسم/عنوان* الزر الجديد:",
            reply_markup=InlineKeyboardMarkup([[btn_cancel()]])); return

    # Choose type (comes from dynbtn_await_type state)
    if data=="dynbtn_type_text":
        context.user_data["dynbtn_new_type"]="text"; context.user_data["state"]="dynbtn_await_content"
        await safe_edit(query,"📝 *نوع: نص*\n\n✏️ أرسل محتوى النص:",reply_markup=InlineKeyboardMarkup([[btn_cancel()]])); return

    if data=="dynbtn_type_list":
        # List buttons don't need extra content — save immediately with empty content
        label   =context.user_data.get("dynbtn_new_label","قائمة جديدة")
        section =context.user_data.get("dynbtn_section","root")
        parent  =context.user_data.get("dynbtn_parent_id",None)
        db_add_btn(parent,section,label,"list","",uid)
        context.user_data.clear()
        await safe_edit(query,f"✅ تم إضافة القائمة *{label}*!\nيمكنك الآن الضغط عليها وإضافة أزرار فرعية.",
            reply_markup=InlineKeyboardMarkup([[btn_back("dynbtn_root"),btn_home()]])); return

    if data=="dynbtn_type_url":
        context.user_data["dynbtn_new_type"]="url"; context.user_data["state"]="dynbtn_await_content"
        await safe_edit(query,"🔗 *نوع: رابط*\n\n✏️ أرسل الرابط الكامل (https://...):",reply_markup=InlineKeyboardMarkup([[btn_cancel()]])); return

    # EDIT button label
    if data.startswith("dynbtn_edit_"):
        if not is_admin(uid): await query.answer("⛔"); return
        bid=int(data.split("_")[2]); btn_row=db_get_btn(bid)
        if not btn_row: await query.answer("⚠️ الزر غير موجود."); return
        context.user_data["state"]="dynbtn_await_edit_label"; context.user_data["dynbtn_edit_id"]=bid
        await safe_edit(query,
            f"✏️ *تعديل اسم الزر #{bid}*\n\nالاسم الحالي: *{btn_row[3]}*\n\nأرسل الاسم الجديد:",
            reply_markup=InlineKeyboardMarkup([[btn_cancel()]])); return

    # EDIT button content
    if data.startswith("dynbtn_editcontent_"):
        if not is_admin(uid): await query.answer("⛔"); return
        bid=int(data.split("_")[2]); btn_row=db_get_btn(bid)
        if not btn_row: await query.answer("⚠️"); return
        context.user_data["state"]="dynbtn_await_edit_content"; context.user_data["dynbtn_edit_id"]=bid
        await safe_edit(query,
            f"✏️ *تعديل محتوى الزر #{bid}*\n\nالمحتوى الحالي:\n_{btn_row[5][:200]}_\n\nأرسل المحتوى الجديد:",
            reply_markup=InlineKeyboardMarkup([[btn_cancel()]])); return

    # DELETE button — with confirmation
    if data.startswith("dynbtn_del_"):
        if not is_admin(uid): await query.answer("⛔"); return
        bid=int(data.split("_")[2]); btn_row=db_get_btn(bid)
        if not btn_row: await query.answer("⚠️"); return
        await safe_edit(query,
            f"🗑 *تأكيد الحذف*\n\nهل تريد حذف الزر: *{btn_row[3]}*?\n⚠️ سيُحذف مع كل محتواه الفرعي!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ نعم، احذف",callback_data=f"dynbtn_confirmdelete_{bid}"),
                 InlineKeyboardButton("❌ إلغاء",   callback_data=f"dynbtn_view_{btn_row[1]}" if btn_row[1] else "dynbtn_root")],
            ])); return

    if data.startswith("dynbtn_confirmdelete_"):
        if not is_admin(uid): await query.answer("⛔"); return
        bid=int(data.split("_")[2]); btn_row=db_get_btn(bid)
        parent_id=btn_row[1] if btn_row else None; section=btn_row[2] if btn_row else "root"
        db_del_btn(bid)
        back_cb=f"dynbtn_view_{parent_id}" if parent_id else "dynbtn_root"
        await safe_edit(query,f"✅ تم حذف الزر وكل محتواه.",
            reply_markup=InlineKeyboardMarkup([[btn_back(back_cb),btn_home()]])); return

    # DELETE child button (pick from list)
    if data.startswith("dynbtn_delchild_"):
        if not is_admin(uid): await query.answer("⛔"); return
        parts=data.split("_",3); section=parts[2]; parent_raw=parts[3]
        parent_id=None if parent_raw=="root" else int(parent_raw)
        children=db_get_children(parent_id,section)
        if not children:
            await safe_edit(query,"⚠️ لا توجد أزرار فرعية.",reply_markup=InlineKeyboardMarkup([[btn_cancel()]])); return
        rows=[[InlineKeyboardButton(f"🗑 {c[1]}",callback_data=f"dynbtn_del_{c[0]}")] for c in children]
        rows.append([btn_cancel()])
        await safe_edit(query,"اختر الزر الذي تريد حذفه:",reply_markup=InlineKeyboardMarkup(rows)); return

    # ══════════════════════════════════════════════════════════════
    # DIRECT REPLY TO INQUIRY
    # ══════════════════════════════════════════════════════════════
    if data.startswith("adm_direct_reply_"):
        if not is_admin(uid): return
        parts=data.split("_"); iid=int(parts[3]); target=int(parts[4])
        context.user_data["state"]="await_reply_text"
        context.user_data["reply_iid"]=iid; context.user_data["reply_target"]=target
        await safe_edit(query,
            f"✏️ *الرد على الاستفسار #{iid}*\n\nاكتب ردك مباشرة وسيُرسل للمستخدم فوراً:",
            reply_markup=InlineKeyboardMarkup([[btn_cancel()]])); return

    # ══════════════════════════════════════════════════════════════
    # ADMIN PANEL
    # ══════════════════════════════════════════════════════════════
    if not is_admin(uid): await query.answer("⛔ ليس لديك صلاحية."); return

    if data=="adm_panel":
        stats=get_admin_stats()
        await safe_edit(query,
            f"⚙️ *لوحة الإدارة*\n\n"
            f"👥 المستخدمون: *{stats['users']}* | 🛡 المشرفون: *{stats['admins']}*\n"
            f"🚫 المحظورون: *{stats['banned']}* | ✅ نشطون: *{stats['active_today']}*\n"
            f"📚 الأحاديث: *{stats['hadiths']}* | 🤲 الأدعية: *{stats['duas']}*\n"
            f"📿 إجمالي التسبيح: *{stats['tasbih_total']}*\n"
            f"🔘 الأزرار الديناميكية: *{stats['dyn_buttons']}*\n"
            f"📋 معلق: *{stats['pending']}* | ✅ مُجاب: *{stats['replied']}*",
            reply_markup=build_admin_keyboard()); return

    if data=="adm_stats":
        stats=get_admin_stats()
        await safe_edit(query,
            f"📊 *إحصائيات البوت*\n\n"
            f"👥 إجمالي المستخدمين: *{stats['users']}*\n"
            f"🛡 المشرفون: *{stats['admins']}*\n"
            f"🚫 المحظورون: *{stats['banned']}*\n"
            f"✅ نشطون اليوم: *{stats['active_today']}*\n"
            f"📚 الأحاديث: *{stats['hadiths']}*\n"
            f"🤲 الأدعية: *{stats['duas']}*\n"
            f"📝 المحتوى: *{stats['content']}*\n"
            f"📿 إجمالي التسبيح: *{stats['tasbih_total']}*\n"
            f"🔘 الأزرار الديناميكية: *{stats['dyn_buttons']}*\n"
            f"📋 معلق: *{stats['pending']}* | ✅ مُجاب: *{stats['replied']}*",
            reply_markup=InlineKeyboardMarkup([[btn_back("adm_panel")]])); return

    if data=="adm_inquiries":
        rows_i=get_pending_inquiries()
        if not rows_i:
            await safe_edit(query,"✅ لا توجد استفسارات معلقة.",reply_markup=InlineKeyboardMarkup([[btn_back("adm_panel")]])); return
        rows_kb=[[InlineKeyboardButton(f"#{r[0]} — {r[3]}: {r[4][:40]}",callback_data=f"adm_direct_reply_{r[0]}_{r[1]}")] for r in rows_i]
        rows_kb.append([btn_back("adm_panel")])
        await safe_edit(query,"📋 *استفسارات معلقة — اضغط للرد مباشرة:*",reply_markup=InlineKeyboardMarkup(rows_kb)); return

    if data=="adm_all_inquiries":
        rows_i=get_all_inquiries(20)
        if not rows_i:
            await safe_edit(query,"لا توجد استفسارات.",reply_markup=InlineKeyboardMarkup([[btn_back("adm_panel")]])); return
        rows_kb=[[InlineKeyboardButton(f"[{r[5]}] #{r[0]} — {r[3]}: {r[4][:35]}",callback_data=f"adm_direct_reply_{r[0]}_{r[1]}")] for r in rows_i]
        rows_kb.append([btn_back("adm_panel")])
        await safe_edit(query,"📜 *كل الاستفسارات — اضغط للرد:*",reply_markup=InlineKeyboardMarkup(rows_kb)); return

    if data=="adm_manage_hadiths":
        con=sqlite3.connect(DB_PATH); rows_h=con.execute("SELECT id,text FROM hadiths ORDER BY id DESC LIMIT 10").fetchall(); con.close()
        lines="\n".join([f"#{r[0]}: {r[1][:50]}…" for r in rows_h]) or "لا توجد أحاديث بعد."
        await safe_edit(query,f"📚 *إدارة الأحاديث*\n\n{lines}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ إضافة",callback_data="adm_add_hadith"),
                 InlineKeyboardButton("🗑 حذف",  callback_data="adm_del_hadith")],
                [btn_back("adm_panel")],
            ])); return

    if data=="adm_add_hadith":
        context.user_data["state"]="await_hadith"
        await safe_edit(query,"✏️ أرسل الحديث بالصيغة:\n\n`نص الحديث | المصدر`",
            reply_markup=InlineKeyboardMarkup([[btn_cancel()]])); return

    if data=="adm_del_hadith":
        con=sqlite3.connect(DB_PATH); rows_h=con.execute("SELECT id,text FROM hadiths ORDER BY id DESC LIMIT 15").fetchall(); con.close()
        if not rows_h: await safe_edit(query,"⚠️ لا توجد أحاديث.",reply_markup=InlineKeyboardMarkup([[btn_back("adm_manage_hadiths")]])); return
        rows_kb=[[InlineKeyboardButton(f"🗑 #{r[0]}: {r[1][:40]}",callback_data=f"adm_dodelh_{r[0]}")] for r in rows_h]
        rows_kb.append([btn_back("adm_manage_hadiths"),btn_cancel()])
        await safe_edit(query,"اختر الحديث للحذف:",reply_markup=InlineKeyboardMarkup(rows_kb)); return

    if data.startswith("adm_dodelh_"):
        hid=int(data.split("_")[2]); con=sqlite3.connect(DB_PATH); con.execute("DELETE FROM hadiths WHERE id=?",(hid,)); con.commit(); con.close()
        await safe_edit(query,f"✅ تم حذف الحديث #{hid}.",reply_markup=InlineKeyboardMarkup([[btn_back("adm_manage_hadiths")]])); return

    if data=="adm_manage_duas":
        con=sqlite3.connect(DB_PATH); rows_d=con.execute("SELECT id,text FROM duas ORDER BY id DESC LIMIT 10").fetchall(); con.close()
        lines="\n".join([f"#{r[0]}: {r[1][:50]}…" for r in rows_d]) or "لا توجد أدعية بعد."
        await safe_edit(query,f"🤲 *إدارة الأدعية*\n\n{lines}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ إضافة",callback_data="adm_add_dua"),
                 InlineKeyboardButton("🗑 حذف",  callback_data="adm_del_dua")],
                [btn_back("adm_panel")],
            ])); return

    if data=="adm_add_dua":
        context.user_data["state"]="await_dua"
        await safe_edit(query,"✏️ أرسل الدعاء:\n\n`نص الدعاء | المصدر`",reply_markup=InlineKeyboardMarkup([[btn_cancel()]])); return

    if data=="adm_del_dua":
        con=sqlite3.connect(DB_PATH); rows_d=con.execute("SELECT id,text FROM duas ORDER BY id DESC LIMIT 15").fetchall(); con.close()
        if not rows_d: await safe_edit(query,"⚠️ لا توجد أدعية.",reply_markup=InlineKeyboardMarkup([[btn_back("adm_manage_duas")]])); return
        rows_kb=[[InlineKeyboardButton(f"🗑 #{r[0]}: {r[1][:40]}",callback_data=f"adm_dodeld_{r[0]}")] for r in rows_d]
        rows_kb.append([btn_back("adm_manage_duas"),btn_cancel()])
        await safe_edit(query,"اختر الدعاء للحذف:",reply_markup=InlineKeyboardMarkup(rows_kb)); return

    if data.startswith("adm_dodeld_"):
        did=int(data.split("_")[2]); con=sqlite3.connect(DB_PATH); con.execute("DELETE FROM duas WHERE id=?",(did,)); con.commit(); con.close()
        await safe_edit(query,f"✅ تم حذف الدعاء #{did}.",reply_markup=InlineKeyboardMarkup([[btn_back("adm_manage_duas")]])); return

    if data=="adm_manage_content":
        con=sqlite3.connect(DB_PATH); rows_c=con.execute("SELECT id,category,text FROM bot_content ORDER BY id DESC LIMIT 10").fetchall(); con.close()
        lines="\n".join([f"#{r[0]} [{r[1]}]: {r[2][:40]}…" for r in rows_c]) or "لا يوجد محتوى."
        await safe_edit(query,f"📝 *إدارة المحتوى*\n\n{lines}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ إضافة",callback_data="adm_add_content"),
                 InlineKeyboardButton("🗑 حذف",  callback_data="adm_del_content")],
                [btn_back("adm_panel")],
            ])); return

    if data=="adm_add_content":
        context.user_data["state"]="await_content"
        await safe_edit(query,"✏️ أرسل:\n\n`الفئة | النص | المصدر`",reply_markup=InlineKeyboardMarkup([[btn_cancel()]])); return

    if data=="adm_del_content":
        con=sqlite3.connect(DB_PATH); rows_c=con.execute("SELECT id,category,text FROM bot_content ORDER BY id DESC LIMIT 15").fetchall(); con.close()
        if not rows_c: await safe_edit(query,"⚠️ لا يوجد محتوى.",reply_markup=InlineKeyboardMarkup([[btn_back("adm_manage_content")]])); return
        rows_kb=[[InlineKeyboardButton(f"🗑 #{r[0]} [{r[1]}]: {r[2][:35]}",callback_data=f"adm_dodelc_{r[0]}")] for r in rows_c]
        rows_kb.append([btn_back("adm_manage_content"),btn_cancel()])
        await safe_edit(query,"اختر المحتوى للحذف:",reply_markup=InlineKeyboardMarkup(rows_kb)); return

    if data.startswith("adm_dodelc_"):
        cid=int(data.split("_")[2]); con=sqlite3.connect(DB_PATH); con.execute("DELETE FROM bot_content WHERE id=?",(cid,)); con.commit(); con.close()
        await safe_edit(query,f"✅ تم الحذف #{cid}.",reply_markup=InlineKeyboardMarkup([[btn_back("adm_manage_content")]])); return

    if data=="adm_add_admin":
        context.user_data["state"]="await_add_admin"
        await safe_edit(query,"✏️ أرسل ID المستخدم لتعيينه مشرفاً:",reply_markup=InlineKeyboardMarkup([[btn_cancel()]])); return

    if data=="adm_del_admin":
        admins=get_all_admins()
        lines="\n".join([str(a) for a in admins if a not in SUPER_ADMINS]) or "لا يوجد مشرفون إضافيون."
        context.user_data["state"]="await_del_admin"
        await safe_edit(query,f"المشرفون الحاليون:\n{lines}\n\nأرسل ID لإزالته:",reply_markup=InlineKeyboardMarkup([[btn_cancel()]])); return

    if data=="adm_ban":
        context.user_data["state"]="await_ban"
        await safe_edit(query,"🚫 أرسل ID المستخدم لحظره:",reply_markup=InlineKeyboardMarkup([[btn_cancel()]])); return

    if data=="adm_unban":
        context.user_data["state"]="await_unban"
        await safe_edit(query,"✅ أرسل ID المستخدم لرفع الحظر:",reply_markup=InlineKeyboardMarkup([[btn_cancel()]])); return

    if data=="adm_broadcast":
        context.user_data["state"]="await_broadcast"
        await safe_edit(query,"📢 أرسل رسالة البث لجميع المستخدمين:",reply_markup=InlineKeyboardMarkup([[btn_cancel()]])); return

    if data=="adm_send_user":
        context.user_data["state"]="await_send_user_id"
        await safe_edit(query,"📩 أرسل ID المستخدم المستهدف:",reply_markup=InlineKeyboardMarkup([[btn_cancel()]])); return

    if data=="adm_users_list":
        rows_u=get_users_list(30)
        lines="\n".join([f"{'🛡' if r[3] else '🚫' if r[4] else '👤'} {r[2] or '—'} | `{r[0]}`" for r in rows_u])
        await safe_edit(query,f"👥 *آخر 30 مستخدم:*\n\n{lines}",reply_markup=InlineKeyboardMarkup([[btn_back("adm_panel")]])); return

    await query.answer("⚠️ أمر غير معروف.")

# ══════════════════════════════════════════════════════════════════
# SCHEDULED JOBS
# ══════════════════════════════════════════════════════════════════
async def job_morning(context:ContextTypes.DEFAULT_TYPE):
    for uid in get_all_users():
        ns=get_notif_settings(uid)
        if not ns.get("morning",1) or notif_already_sent(uid,"morning"): continue
        try:
            await context.bot.send_message(uid,
                "🌅 *صباح النور!*\n\n"
                "ابدأ يومك بذكر الله 🌿\n"
                "قال ﷺ: _من قال حين يصبح وحين يمسي: سبحان الله وبحمده مئة مرة، لم يأتِ أحد يوم القيامة بأفضل مما جاء به_\n\n"
                "اضغط /start لأذكار الصباح 🤲",
                parse_mode=ParseMode.MARKDOWN)
            mark_notif_sent(uid,"morning")
        except: pass

async def job_evening(context:ContextTypes.DEFAULT_TYPE):
    for uid in get_all_users():
        ns=get_notif_settings(uid)
        if not ns.get("evening",1) or notif_already_sent(uid,"evening"): continue
        try:
            await context.bot.send_message(uid,
                "🌆 *حان وقت أذكار المساء!*\n\n"
                "لا تنسَ حمى ربك لليلتك 🌙\n"
                "قال ﷺ: _من قرأ آية الكرسي حين يمسي، أُجير من الجن حتى يصبح_\n\n"
                "اضغط /start لأذكار المساء 🤲",
                parse_mode=ParseMode.MARKDOWN)
            mark_notif_sent(uid,"evening")
        except: pass

async def job_wird(context:ContextTypes.DEFAULT_TYPE):
    for uid in get_all_users():
        ns=get_notif_settings(uid)
        if not ns.get("wird",1) or notif_already_sent(uid,"wird"): continue
        surah,ayah=get_wird_progress(uid); sname=SURAH_NAMES.get(surah,str(surah))
        try:
            await context.bot.send_message(uid,
                f"🌿 *تذكير الورد اليومي* 📖\n\n"
                f"أنت في سورة *{sname}* — آية {ayah}\n"
                f"_قال ﷺ: أحب الأعمال إلى الله أدومها وإن قلّ_\n\n"
                f"اضغط /start للمتابعة 📖",
                parse_mode=ParseMode.MARKDOWN)
            mark_notif_sent(uid,"wird")
        except: pass

async def job_friday(context:ContextTypes.DEFAULT_TYPE):
    if datetime.now().weekday()!=4: return
    for uid in get_all_users():
        ns=get_notif_settings(uid)
        if not ns.get("friday",1) or notif_already_sent(uid,"friday"): continue
        try:
            await context.bot.send_message(uid,
                "⭐ *جمعة مباركة!*\n\n"
                "📖 لا تنسَ قراءة سورة الكهف اليوم\n"
                "🤲 أكثر من الصلاة على النبي ﷺ\n"
                "⏰ احرص على ساعة الاستجابة آخر ساعة قبل المغرب\n\n"
                "_تقبّل الله منك وبارك في جمعتك_ 🌟",
                parse_mode=ParseMode.MARKDOWN)
            mark_notif_sent(uid,"friday")
        except: pass

# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════
def main():
    init_db()
    app=ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,handle_message))
    jq=app.job_queue
    if jq:
        jq.run_daily(job_morning, time=time(5, 30, tzinfo=timezone.utc))
        jq.run_daily(job_evening, time=time(16, 0, tzinfo=timezone.utc))
        jq.run_daily(job_wird,    time=time(8,  0, tzinfo=timezone.utc))
        jq.run_daily(job_friday,  time=time(6,  0, tzinfo=timezone.utc))
        logger.info("✅ JobQueue مفعّل.")
    else:
        logger.warning("⚠️ JobQueue غير متاح — ثبّت: pip install 'python-telegram-bot[job-queue]'")
    logger.info("🤖 البوت يعمل...")
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
