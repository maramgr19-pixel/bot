import os, random, sqlite3, logging, asyncio, aiohttp, json
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
    ("اللّهُ لاَ إِلَـهَ إِلاَّ هُوَ الْحَيُّ الْقَيُّومُ لاَ تَأْخُذُهُ سِنَةٌ وَلاَ نَوْمٌ لَّهُ مَا فِي السَّمَاوَاتِ وَمَا فِي الأَرْضِ مَن ذَا الَّذِي يَشْفَعُ عِنْدَهُ إِلاَّ بِإِذْنِهِ يَعْلَمُ مَا بَيْنَ أَيْدِيهِمْ وَمَا خَلْفَهُمْ وَلاَ يُحِيطُونَ بِشَيْءٍ مِّنْ عِلْمِهِ إِلاَّ بِمَا شَاء وَسِعَ كُرْسِيُّهُ السَّمَاوَاتِ وَالأَرْضَ وَلاَ يَؤُودُهُ حِفْظُهُمَا وَهُوَ الْعَلِيُّ الْعَظِيمُ\n[البقرة: 255] — آية الكرسي", "١ مرة — من قالها حين يصبح أُجير من الجن حتى يمسي | رواه النسائي صحيح", 1),
    ("أَصْبَحْنَا وَأَصْبَحَ الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ، لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ، رَبِّ أَسْأَلُكَ خَيْرَ مَا فِي هَذَا الْيَوْمِ وَخَيْرَ مَا بَعْدَهُ، وَأَعُوذُ بِكَ مِنْ شَرِّ مَا فِي هَذَا الْيَوْمِ وَشَرِّ مَا بَعْدَهُ.", "١ مرة — رواه مسلم", 1),
    ("اللَّهُمَّ بِكَ أَصْبَحْنَا، وَبِكَ أَمْسَيْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ النُّشُورُ.", "١ مرة — رواه الترمذي صحيح", 1),
    ("اللَّهُمَّ أَنْتَ رَبِّي لَا إِلَهَ إِلَّا أَنْتَ، خَلَقْتَنِي وَأَنَا عَبْدُكَ، وَأَنَا عَلَى عَهْدِكَ وَوَعْدِكَ مَا اسْتَطَعْتُ، أَعُوذُ بِكَ مِنْ شَرِّ مَا صَنَعْتُ، أَبُوءُ لَكَ بِنِعْمَتِكَ عَلَيَّ، وَأَبُوءُ بِذَنْبِي فَاغْفِرْ لِي فَإِنَّهُ لَا يَغْفِرُ الذُّنُوبَ إِلَّا أَنْتَ.", "١ مرة — سيد الاستغفار | رواه البخاري", 1),
    ("اللَّهُمَّ إِنِّي أَصْبَحْتُ أُشْهِدُكَ، وَأُشْهِدُ حَمَلَةَ عَرْشِكَ، وَمَلَائِكَتَكَ، وَجَمِيعَ خَلْقِكَ، أَنَّكَ أَنْتَ اللَّهُ لَا إِلَهَ إِلَّا أَنْتَ وَحْدَكَ لَا شَرِيكَ لَكَ، وَأَنَّ مُحَمَّدًا عَبْدُكَ وَرَسُولُكَ.", "٤ مرات — رواه أبو داود صحيح", 4),
    ("اللَّهُمَّ مَا أَصْبَحَ بِي مِنْ نِعْمَةٍ أَوْ بِأَحَدٍ مِنْ خَلْقِكَ، فَمِنْكَ وَحْدَكَ لَا شَرِيكَ لَكَ، فَلَكَ الْحَمْدُ وَلَكَ الشُّكْرُ.", "١ مرة — رواه أبو داود صحيح", 1),
    ("اللَّهُمَّ عَافِنِي فِي بَدَنِي، اللَّهُمَّ عَافِنِي فِي سَمْعِي، اللَّهُمَّ عَافِنِي فِي بَصَرِي، لَا إِلَهَ إِلَّا أَنْتَ.\nاللَّهُمَّ إِنِّي أَعُوذُ بِكَ مِنَ الْكُفْرِ وَالْفَقْرِ، وَأَعُوذُ بِكَ مِنْ عَذَابِ الْقَبْرِ، لَا إِلَهَ إِلَّا أَنْتَ.", "٣ مرات — رواه أبو داود صحيح", 3),
    ("حَسْبِيَ اللَّهُ لَا إِلَهَ إِلَّا هُوَ، عَلَيْهِ تَوَكَّلْتُ وَهُوَ رَبُّ الْعَرْشِ الْعَظِيمِ.", "٧ مرات — رواه أبو داود صحيح", 7),
    ("بِسْمِ اللَّهِ الَّذِي لَا يَضُرُّ مَعَ اسْمِهِ شَيْءٌ فِي الْأَرْضِ وَلَا فِي السَّمَاءِ وَهُوَ السَّمِيعُ الْعَلِيمُ.", "٣ مرات — رواه أبو داود والترمذي صحيح", 3),
    ("رَضِيتُ بِاللَّهِ رَبًّا، وَبِالْإِسْلَامِ دِينًا، وَبِمُحَمَّدٍ صلى الله عليه وسلم نَبِيًّا.", "٣ مرات — رواه أبو داود صحيح", 3),
    ("سُبْحَانَ اللَّهِ وَبِحَمْدِهِ.", "١٠٠ مرة — رواه مسلم", 100),
    ("لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ، وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ.", "١٠ مرات — رواه أحمد صحيح", 10),
    ("اللَّهُمَّ إِنِّي أَسْأَلُكَ الْعَفْوَ وَالْعَافِيَةَ فِي الدُّنْيَا وَالْآخِرَةِ.\nاللَّهُمَّ اسْتُرْ عَوْرَاتِي وَآمِنْ رَوْعَاتِي.\nاللَّهُمَّ احْفَظْنِي مِنْ بَيْنِ يَدَيَّ وَمِنْ خَلْفِي وَعَنْ يَمِينِي وَعَنْ شِمَالِي وَمِنْ فَوْقِي.", "١ مرة — رواه أبو داود وابن ماجه صحيح", 1),
    ("اللَّهُمَّ عَالِمَ الْغَيْبِ وَالشَّهَادَةِ، فَاطِرَ السَّمَاوَاتِ وَالْأَرْضِ، رَبَّ كُلِّ شَيْءٍ وَمَلِيكَهُ، أَشْهَدُ أَنْ لَا إِلَهَ إِلَّا أَنْتَ، أَعُوذُ بِكَ مِنْ شَرِّ نَفْسِي وَمِنْ شَرِّ الشَّيْطَانِ وَشِرْكِهِ.", "١ مرة — رواه الترمذي وأبو داود صحيح", 1),
    ("قُلْ هُوَ اللَّهُ أَحَدٌ — قُلْ أَعُوذُ بِرَبِّ الْفَلَقِ — قُلْ أَعُوذُ بِرَبِّ النَّاسِ", "٣ مرات لكل سورة — رواه أبو داود والترمذي صحيح", 3),
]

EVENING_ADHKAR = [
    ("اللَّهُ لَا إِلَهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ لَا تَأْخُذُهُ سِنَةٌ وَلَا نَوْمٌ لَهُ مَا فِي السَّمَاوَاتِ وَمَا فِي الْأَرْضِ مَنْ ذَا الَّذِي يَشْفَعُ عِنْدَهُ إِلَّا بِإِذْنِهِ يَعْلَمُ مَا بَيْنَ أَيْدِيهِمْ وَمَا خَلْفَهُمْ وَلَا يُحِيطُونَ بِشَيْءٍ مِنْ عِلْمِهِ إِلَّا بِمَا شَاءَ وَسِعَ كُرْسِيُّهُ السَّمَاوَاتِ وَالْأَرْضَ وَلَا يَئُودُهُ حِفْظُهُمَا وَهُوَ الْعَلِيُّ الْعَظِيمُ\n[البقرة: 255]", "١ مرة — من قالها حين يمسي أُجير من الجن حتى يصبح | رواه النسائي صحيح", 1),
    ("أَمْسَيْنَا وَأَمْسَى الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ، لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ، رَبِّ أَسْأَلُكَ خَيْرَ مَا فِي هَذِهِ اللَّيْلَةِ وَخَيْرَ مَا بَعْدَهَا، وَأَعُوذُ بِكَ مِنْ شَرِّ مَا فِي هَذِهِ اللَّيْلَةِ وَشَرِّ مَا بَعْدَهَا.", "١ مرة — رواه مسلم", 1),
    ("اللَّهُمَّ بِكَ أَمْسَيْنَا، وَبِكَ أَصْبَحْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ الْمَصِيرُ.", "١ مرة — رواه الترمذي صحيح", 1),
    ("اللَّهُمَّ أَنْتَ رَبِّي لَا إِلَهَ إِلَّا أَنْتَ، خَلَقْتَنِي وَأَنَا عَبْدُكَ، وَأَنَا عَلَى عَهْدِكَ وَوَعْدِكَ مَا اسْتَطَعْتُ، أَعُوذُ بِكَ مِنْ شَرِّ مَا صَنَعْتُ، أَبُوءُ لَكَ بِنِعْمَتِكَ عَلَيَّ، وَأَبُوءُ بِذَنْبِي فَاغْفِرْ لِي فَإِنَّهُ لَا يَغْفِرُ الذُّنُوبَ إِلَّا أَنْتَ.", "١ مرة — سيد الاستغفار | رواه البخاري", 1),
    ("أَعُوذُ بِكَلِمَاتِ اللَّهِ التَّامَّاتِ مِنْ شَرِّ مَا خَلَقَ.", "٣ مرات — رواه مسلم", 3),
    ("بِسْمِ اللَّهِ الَّذِي لَا يَضُرُّ مَعَ اسْمِهِ شَيْءٌ فِي الْأَرْضِ وَلَا فِي السَّمَاءِ وَهُوَ السَّمِيعُ الْعَلِيمُ.", "٣ مرات — رواه أبو داود صحيح", 3),
    ("حَسْبِيَ اللَّهُ لَا إِلَهَ إِلَّا هُوَ، عَلَيْهِ تَوَكَّلْتُ وَهُوَ رَبُّ الْعَرْشِ الْعَظِيمِ.", "٧ مرات — رواه أبو داود صحيح", 7),
    ("سُبْحَانَ اللَّهِ وَبِحَمْدِهِ.", "١٠٠ مرة — رواه مسلم", 100),
    ("اللَّهُمَّ إِنِّي أَمْسَيْتُ أُشْهِدُكَ، وَأُشْهِدُ حَمَلَةَ عَرْشِكَ، وَمَلَائِكَتَكَ، وَجَمِيعَ خَلْقِكَ، أَنَّكَ أَنْتَ اللَّهُ لَا إِلَهَ إِلَّا أَنْتَ وَحْدَكَ لَا شَرِيكَ لَكَ، وَأَنَّ مُحَمَّدًا عَبْدُكَ وَرَسُولُكَ.", "٤ مرات — رواه أبو داود صحيح", 4),
    ("اللَّهُمَّ مَا أَمْسَى بِي مِنْ نِعْمَةٍ أَوْ بِأَحَدٍ مِنْ خَلْقِكَ، فَمِنْكَ وَحْدَكَ لَا شَرِيكَ لَكَ، فَلَكَ الْحَمْدُ وَلَكَ الشُّكْرُ.", "١ مرة — رواه أبو داود صحيح", 1),
    ("قُلْ هُوَ اللَّهُ أَحَدٌ — قُلْ أَعُوذُ بِرَبِّ الْفَلَقِ — قُلْ أَعُوذُ بِرَبِّ النَّاسِ", "٣ مرات لكل سورة — رواه أبو داود والترمذي صحيح", 3),
]

SLEEP_ADHKAR = [
    ("بِاسْمِكَ رَبِّي وَضَعْتُ جَنْبِي، وَبِكَ أَرْفَعُهُ، فَإِنْ أَمْسَكْتَ نَفْسِي فَارْحَمْهَا، وَإِنْ أَرْسَلْتَهَا فَاحْفَظْهَا بِمَا تَحْفَظُ بِهِ عِبَادَكَ الصَّالِحِينَ.", "١ مرة — رواه البخاري ومسلم", 1),
    ("اللَّهُمَّ إِنَّكَ خَلَقْتَ نَفْسِي وَأَنْتَ تَوَفَّاهَا، لَكَ مَمَاتُهَا وَمَحْيَاهَا، إِنْ أَحْيَيْتَهَا فَاحْفَظْهَا، وَإِنْ أَمَتَّهَا فَاغْفِرْ لَهَا.", "١ مرة — رواه مسلم", 1),
    ("اللَّهُمَّ قِنِي عَذَابَكَ يَوْمَ تَبْعَثُ عِبَادَكَ.", "٣ مرات — رواه أبو داود صحيح", 3),
    ("بِاسْمِكَ اللَّهُمَّ أَمُوتُ وَأَحْيَا.", "١ مرة — رواه البخاري", 1),
    ("الْحَمْدُ لِلَّهِ الَّذِي أَطْعَمَنَا وَسَقَانَا، وَكَفَانَا، وَآوَانَا، فَكَمْ مِمَّنْ لَا كَافِيَ لَهُ وَلَا مُؤْوِيَ.", "١ مرة — رواه مسلم", 1),
    ("سُبْحَانَ اللَّهِ (٣٣) — الْحَمْدُ لِلَّهِ (٣٣) — اللَّهُ أَكْبَرُ (٣٤) — تسبيح فاطمة الزهراء رضي الله عنها", "رواه البخاري ومسلم", 1),
    ("اللَّهُ لَا إِلَهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ...\n[البقرة: 255] — آية الكرسي", "١ مرة — لم يزل عليه من الله حافظ | رواه البخاري", 1),
    ("اللَّهُمَّ أَسْلَمْتُ نَفْسِي إِلَيْكَ، وَفَوَّضْتُ أَمْرِي إِلَيْكَ، وَوَجَّهْتُ وَجْهِي إِلَيْكَ، وَأَلْجَأْتُ ظَهْرِي إِلَيْكَ، رَغْبَةً وَرَهْبَةً إِلَيْكَ، لَا مَلْجَأَ وَلَا مَنْجَا مِنْكَ إِلَّا إِلَيْكَ، آمَنْتُ بِكِتَابِكَ الَّذِي أَنْزَلْتَ وَبِنَبِيِّكَ الَّذِي أَرْسَلْتَ.\n(اجعلها آخر كلامك قبل النوم)", "١ مرة — رواه البخاري ومسلم", 1),
]

WAKEUP_ADHKAR = [
    ("الْحَمْدُ لِلَّهِ الَّذِي أَحْيَانَا بَعْدَ مَا أَمَاتَنَا وَإِلَيْهِ النُّشُورُ.", "١ مرة — رواه البخاري", 1),
    ("لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ، وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ، سُبْحَانَ اللَّهِ، وَالْحَمْدُ لِلَّهِ، وَلَا إِلَهَ إِلَّا اللَّهُ، وَاللَّهُ أَكْبَرُ، وَلَا حَوْلَ وَلَا قُوَّةَ إِلَّا بِاللَّهِ الْعَلِيِّ الْعَظِيمِ، رَبِّ اغْفِرْ لِي.", "١ مرة — رواه البخاري", 1),
]

WUDU_ADHKAR = [
    ("بِسْمِ اللَّهِ.", "عند البدء — رواه أبو داود صحيح", 1),
    ("أَشْهَدُ أَنْ لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ وَأَشْهَدُ أَنَّ مُحَمَّدًا عَبْدُهُ وَرَسُولُهُ، اللَّهُمَّ اجْعَلْنِي مِنَ التَّوَّابِينَ وَاجْعَلْنِي مِنَ الْمُتَطَهِّرِينَ.", "بعد الوضوء — رواه مسلم", 1),
    ("سُبْحَانَكَ اللَّهُمَّ وَبِحَمْدِكَ أَشْهَدُ أَنْ لَا إِلَهَ إِلَّا أَنْتَ أَسْتَغْفِرُكَ وَأَتُوبُ إِلَيْكَ.", "بعد الوضوء — رواه النسائي صحيح", 1),
]

PRAYER_ADHKAR = {
    "الأذان": [
        ("ترديد كلمات المؤذن مع المؤذن. عند الحيعلتين يقول: لَا حَوْلَ وَلَا قُوَّةَ إِلَّا بِاللَّهِ.", "رواه مسلم", 1),
        ("اللَّهُمَّ رَبَّ هَذِهِ الدَّعْوَةِ التَّامَّةِ وَالصَّلَاةِ الْقَائِمَةِ آتِ مُحَمَّدًا الْوَسِيلَةَ وَالْفَضِيلَةَ وَابْعَثْهُ مَقَامًا مَحْمُودًا الَّذِي وَعَدْتَهُ.", "بعد الأذان — رواه البخاري", 1),
    ],
    "دعاء الاستفتاح": [
        ("سُبْحَانَكَ اللَّهُمَّ وَبِحَمْدِكَ وَتَبَارَكَ اسْمُكَ وَتَعَالَى جَدُّكَ وَلَا إِلَهَ غَيْرُكَ.", "رواه الترمذي وأبو داود", 1),
        ("اللَّهُمَّ بَاعِدْ بَيْنِي وَبَيْنَ خَطَايَايَ كَمَا بَاعَدْتَ بَيْنَ الْمَشْرِقِ وَالْمَغْرِبِ.", "رواه البخاري ومسلم", 1),
    ],
    "ذكر الركوع": [
        ("سُبْحَانَ رَبِّيَ الْعَظِيمِ.", "٣ مرات — رواه مسلم", 3),
        ("سُبْحَانَكَ اللَّهُمَّ رَبَّنَا وَبِحَمْدِكَ اللَّهُمَّ اغْفِرْ لِي.", "رواه البخاري ومسلم", 1),
    ],
    "الرفع من الركوع": [
        ("سَمِعَ اللَّهُ لِمَنْ حَمِدَهُ.", "رواه البخاري ومسلم", 1),
        ("رَبَّنَا وَلَكَ الْحَمْدُ حَمْدًا كَثِيرًا طَيِّبًا مُبَارَكًا فِيهِ.", "رواه البخاري", 1),
    ],
    "ذكر السجود": [
        ("سُبْحَانَ رَبِّيَ الْأَعْلَى.", "٣ مرات — رواه مسلم", 3),
        ("اللَّهُمَّ اغْفِرْ لِي ذَنْبِي كُلَّهُ دِقَّهُ وَجِلَّهُ وَأَوَّلَهُ وَآخِرَهُ وَعَلَانِيَتَهُ وَسِرَّهُ.", "رواه مسلم", 1),
    ],
    "الجلوس بين السجدتين": [
        ("رَبِّ اغْفِرْ لِي، رَبِّ اغْفِرْ لِي.", "رواه أبو داود صحيح", 1),
        ("اللَّهُمَّ اغْفِرْ لِي وَارْحَمْنِي وَعَافِنِي وَاهْدِنِي وَارْزُقْنِي.", "رواه الترمذي صحيح", 1),
    ],
    "التشهد": [
        ("التَّحِيَّاتُ لِلَّهِ وَالصَّلَوَاتُ وَالطَّيِّبَاتُ، السَّلَامُ عَلَيْكَ أَيُّهَا النَّبِيُّ وَرَحْمَةُ اللَّهِ وَبَرَكَاتُهُ، السَّلَامُ عَلَيْنَا وَعَلَى عِبَادِ اللَّهِ الصَّالِحِينَ، أَشْهَدُ أَنْ لَا إِلَهَ إِلَّا اللَّهُ وَأَشْهَدُ أَنَّ مُحَمَّدًا عَبْدُهُ وَرَسُولُهُ.", "متفق عليه", 1),
    ],
    "الصلاة الإبراهيمية": [
        ("اللَّهُمَّ صَلِّ عَلَى مُحَمَّدٍ وَعَلَى آلِ مُحَمَّدٍ كَمَا صَلَّيْتَ عَلَى إِبْرَاهِيمَ وَعَلَى آلِ إِبْرَاهِيمَ إِنَّكَ حَمِيدٌ مَجِيدٌ.", "متفق عليه", 1),
    ],
    "دعاء قبل السلام": [
        ("اللَّهُمَّ إِنِّي أَعُوذُ بِكَ مِنْ عَذَابِ جَهَنَّمَ، وَمِنْ عَذَابِ الْقَبْرِ، وَمِنْ فِتْنَةِ الْمَحْيَا وَالْمَمَاتِ، وَمِنْ شَرِّ فِتْنَةِ الْمَسِيحِ الدَّجَّالِ.", "رواه البخاري ومسلم", 1),
    ],
    "أذكار بعد الصلاة": [
        ("أَسْتَغْفِرُ اللَّهَ (٣ مرات)، ثم: اللَّهُمَّ أَنْتَ السَّلَامُ وَمِنْكَ السَّلَامُ تَبَارَكْتَ يَا ذَا الْجَلَالِ وَالْإِكْرَامِ.", "رواه مسلم", 1),
        ("سُبْحَانَ اللَّهِ ٣٣ — الْحَمْدُ لِلَّهِ ٣٣ — اللَّهُ أَكْبَرُ ٣٣ — ثم: لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ.", "رواه مسلم", 1),
        ("قراءة آية الكرسي دبر كل صلاة مكتوبة.", "رواه النسائي صحيح", 1),
        ("اللَّهُمَّ أَعِنِّي عَلَى ذِكْرِكَ وَشُكْرِكَ وَحُسْنِ عِبَادَتِكَ.", "رواه أبو داود والنسائي صحيح", 1),
    ],
}

WOMAN_ADHKAR = {
    "دعاء طلب العلم النافع": [
        ("اللَّهُمَّ إِنِّي أَسْأَلُكَ عِلْمًا نَافِعًا، وَرِزْقًا طَيِّبًا، وَعَمَلًا مُتَقَبَّلًا.", "رواه ابن ماجه صحيح", 1),
        ("رَبِّ زِدْنِي عِلْمًا.", "سورة طه: ١١٤", 1),
    ],
    "دعاء تيسير الأمور": [
        ("اللَّهُمَّ لَا سَهْلَ إِلَّا مَا جَعَلْتَهُ سَهْلًا، وَأَنْتَ تَجْعَلُ الْحَزْنَ إِذَا شِئْتَ سَهْلًا.", "رواه ابن السني صحيح", 1),
        ("حَسْبُنَا اللَّهُ وَنِعْمَ الْوَكِيلُ.", "سورة آل عمران: ١٧٣", 1),
    ],
    "دعاء القلب والطمأنينة": [
        ("اللَّهُمَّ اجْعَلِ الْقُرْآنَ رَبِيعَ قَلْبِي، وَنُورَ صَدْرِي، وَجَلَاءَ حُزْنِي، وَذَهَابَ هَمِّي.", "رواه أحمد صحيح", 1),
    ],
    "دعاء الصبر والثبات": [
        ("رَبَّنَا أَفْرِغْ عَلَيْنَا صَبْرًا وَثَبِّتْ أَقْدَامَنَا وَانصُرْنَا عَلَى الْقَوْمِ الْكَافِرِينَ.", "سورة البقرة: ٢٥٠", 1),
    ],
}

SPECIAL_DUAS = {
    "دعاء الهم والحزن": [
        ("اللَّهُمَّ إِنِّي عَبْدُكَ ابْنُ عَبْدِكَ ابْنُ أَمَتِكَ، نَاصِيَتِي بِيَدِكَ، مَاضٍ فِيَّ حُكْمُكَ، عَدْلٌ فِيَّ قَضَاؤُكَ، أَسْأَلُكَ بِكُلِّ اسْمٍ هُوَ لَكَ أَنْ تَجْعَلَ الْقُرْآنَ رَبِيعَ قَلْبِي وَنُورَ صَدْرِي وَجَلَاءَ حُزْنِي وَذَهَابَ هَمِّي.", "رواه أحمد صحيح", 1),
        ("لَا إِلَهَ إِلَّا اللَّهُ الْعَظِيمُ الْحَلِيمُ، لَا إِلَهَ إِلَّا اللَّهُ رَبُّ الْعَرْشِ الْعَظِيمِ.", "متفق عليه — دعاء الكرب", 1),
    ],
    "دعاء الكرب الشديد": [
        ("لَا إِلَهَ إِلَّا أَنْتَ سُبْحَانَكَ إِنِّي كُنْتُ مِنَ الظَّالِمِينَ.", "دعاء ذي النون — سورة الأنبياء: ٨٧", 1),
    ],
    "دعاء الاستغفار": [
        ("أَسْتَغْفِرُ اللَّهَ الَّذِي لَا إِلَهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ وَأَتُوبُ إِلَيْهِ.", "رواه الترمذي صحيح", 1),
        ("رَبِّ اغْفِرْ لِي وَتُبْ عَلَيَّ إِنَّكَ أَنْتَ التَّوَّابُ الرَّحِيمُ.", "رواه الترمذي صحيح — ١٠٠ مرة في المجلس", 100),
    ],
    "دعاء طلب الرزق": [
        ("اللَّهُمَّ اكْفِنِي بِحَلَالِكَ عَنْ حَرَامِكَ وَأَغْنِنِي بِفَضْلِكَ عَمَّنْ سِوَاكَ.", "رواه الترمذي حسن", 1),
    ],
    "دعاء الشفاء": [
        ("اللَّهُمَّ رَبَّ النَّاسِ أَذْهِبِ الْبَأْسَ، اشْفِ أَنْتَ الشَّافِي، لَا شِفَاءَ إِلَّا شِفَاؤُكَ، شِفَاءً لَا يُغَادِرُ سَقَمًا.", "متفق عليه", 1),
        ("أَسْأَلُ اللَّهَ الْعَظِيمَ رَبَّ الْعَرْشِ الْعَظِيمِ أَنْ يَشْفِيَكَ.", "٧ مرات — رواه الترمذي صحيح", 7),
    ],
    "دعاء عند البلاء": [
        ("إِنَّا لِلَّهِ وَإِنَّا إِلَيْهِ رَاجِعُونَ، اللَّهُمَّ أْجُرْنِي فِي مُصِيبَتِي وَأَخْلِفْ لِي خَيْرًا مِنْهَا.", "رواه مسلم", 1),
    ],
    "دعاء التوبة": [
        ("رَبَّنَا ظَلَمْنَا أَنْفُسَنَا وَإِنْ لَمْ تَغْفِرْ لَنَا وَتَرْحَمْنَا لَنَكُونَنَّ مِنَ الْخَاسِرِينَ.", "سورة الأعراف: ٢٣", 1),
    ],
}

TASBIH_LIST = [
    ("سُبْحَانَ اللَّهِ",                                           "تمحو الخطايا — رواه مسلم",              33),
    ("الْحَمْدُ لِلَّهِ",                                           "تملأ الميزان — رواه مسلم",               33),
    ("اللَّهُ أَكْبَرُ",                                            "تملأ ما بين السماء والأرض",               33),
    ("لَا إِلَهَ إِلَّا اللَّهُ",                                   "أفضل الذكر — رواه الترمذي",              100),
    ("لَا حَوْلَ وَلَا قُوَّةَ إِلَّا بِاللَّهِ",                 "كنز من كنوز الجنة — متفق عليه",          100),
    ("سُبْحَانَ اللَّهِ وَبِحَمْدِهِ سُبْحَانَ اللَّهِ الْعَظِيمِ","أحب الكلام إلى الله — متفق عليه",       100),
    ("أَسْتَغْفِرُ اللَّهَ",                                        "من لزمه فتح الله له كل مضيق — أبو داود", 100),
    ("اللَّهُمَّ صَلِّ وَسَلِّمْ عَلَى نَبِيِّنَا مُحَمَّدٍ",    "من صلى عليه مرة صلى الله عليه عشرا",    100),
    ("سُبْحَانَ اللَّهِ وَبِحَمْدِهِ",                             "من قالها مئة غُفرت خطاياه — البخاري",    100),
    ("اللَّهُمَّ اغْفِرْ لِي وَتُبْ عَلَيَّ",                     "رواه أبو داود صحيح",                      100),
]

FRIDAY_SUNNAN = [
    {"title": "الاغتسال يوم الجمعة", "text": "الاغتسال يوم الجمعة واجب على كل محتلم.\nقال النبي صلى الله عليه وسلم: غسل الجمعة واجب على كل محتلم.", "source": "متفق عليه"},
    {"title": "التبكير إلى الجمعة",  "text": "التبكير إلى صلاة الجمعة.\nمن راح في الساعة الأولى فكأنما قرّب بدنة، ومن راح في الساعة الثانية فكأنما قرّب بقرة.", "source": "متفق عليه"},
    {"title": "الصلاة على النبي",    "text": "أَكْثِرُوا الصَّلَاةَ عَلَيَّ يَوْمَ الجُمُعَةِ وَلَيْلَةَ الجُمُعَةِ، فَمَنْ صَلَّى عَلَيَّ صَلَاةً صَلَّى اللَّهُ عَلَيْهِ عَشْرًا.", "source": "رواه البيهقي صحيح"},
    {"title": "ساعة الاستجابة",       "text": "في الجمعة ساعة لا يوافقها عبد مسلم وهو قائم يصلي يسأل الله شيئاً إلا أعطاه إياه.\nأرجح الأقوال أنها آخر ساعة بعد العصر حتى المغرب.", "source": "متفق عليه"},
]

FRIDAY_SURAHS = {
    18: "سورة الكهف — أضاء له النور ما بين الجمعتين",
    36: "سورة يس — قلب القرآن",
    67: "سورة الملك — تشفع لصاحبها",
}

ALGERIAN_CITIES = [
    "Algiers","Oran","Constantine","Annaba","Blida",
    "Batna","Sétif","Sidi Bel Abbès","Biskra","Béjaïa",
    "Tlemcen","Béchar","Mostaganem","Skikda","Chlef",
    "Souk Ahras","Tiaret","M'Sila","Djelfa","Tizi Ouzou",
    "Ouargla","Ghardaïa","El Oued","Tamanrasset","Adrar",
]

MOTIVATION_MSGS = [
    "🌺 ما شاء الله! أتممت هذا الذكر. بارك الله فيك.",
    "🌟 أحسنت! كل كلمة طيبة تزرعها اليوم ستجني ثمارها في الآخرة.",
    "💫 رائع! قال النبي ﷺ: أحب الأعمال إلى الله أدومها وإن قلّ.",
    "🌸 بارك الله فيك! الملائكة تكتب حسناتك الآن.",
    "🌺 جزاك الله خيراً! المواظبة هي طريق الفلاح.",
]

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
            user_id INTEGER PRIMARY KEY, surah INTEGER NOT NULL DEFAULT 2, ayah INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS surah_progress (
            user_id INTEGER NOT NULL, surah INTEGER NOT NULL,
            riwaya TEXT NOT NULL DEFAULT 'hafs', last_ayah INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, surah, riwaya)
        );
        CREATE TABLE IF NOT EXISTS tasbih_log (
            user_id INTEGER NOT NULL, log_date TEXT NOT NULL,
            phrase TEXT NOT NULL, count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, log_date, phrase)
        );
        CREATE TABLE IF NOT EXISTS adhkar_progress (
            user_id INTEGER NOT NULL, adhkar_key TEXT NOT NULL,
            idx INTEGER NOT NULL DEFAULT 0, done_date TEXT NOT NULL DEFAULT '',
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
        CREATE TABLE IF NOT EXISTS custom_buttons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section TEXT NOT NULL, btn_label TEXT NOT NULL,
            btn_content TEXT NOT NULL, added_by INTEGER,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    con.commit(); con.close()

def upsert_user(uid, username, first_name, last_name=None):
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        INSERT INTO users (user_id, username, first_name, last_name, last_seen)
        VALUES (?,?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username, first_name=excluded.first_name,
            last_name=excluded.last_name, last_seen=excluded.last_seen
    """, (uid, username, first_name, last_name, datetime.now().isoformat()))
    con.commit(); con.close()

def is_admin(uid):
    if uid in SUPER_ADMINS: return True
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT is_admin FROM users WHERE user_id=?", (uid,)).fetchone()
    con.close()
    return bool(row and row[0])

def is_banned(uid):
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT is_banned FROM users WHERE user_id=?", (uid,)).fetchone()
    con.close()
    return bool(row and row[0])

def get_random_hadith():
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT text, source FROM hadiths ORDER BY RANDOM() LIMIT 1").fetchone()
    con.close(); return row

def get_random_dua():
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT text, source FROM duas ORDER BY RANDOM() LIMIT 1").fetchone()
    con.close(); return row

def save_wird_progress(uid, surah, ayah):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO wird_progress (user_id, surah, ayah) VALUES (?,?,?) ON CONFLICT(user_id) DO UPDATE SET surah=excluded.surah, ayah=excluded.ayah", (uid, surah, ayah))
    con.commit(); con.close()

def get_wird_progress(uid):
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT surah, ayah FROM wird_progress WHERE user_id=?", (uid,)).fetchone()
    con.close()
    return (row[0], row[1]) if row else (2, 1)

def save_surah_progress(uid, surah, ayah, riwaya="hafs"):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO surah_progress (user_id, surah, riwaya, last_ayah) VALUES (?,?,?,?) ON CONFLICT(user_id, surah, riwaya) DO UPDATE SET last_ayah=excluded.last_ayah", (uid, surah, riwaya, ayah))
    con.commit(); con.close()

def get_surah_progress(uid, surah, riwaya="hafs"):
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT last_ayah FROM surah_progress WHERE user_id=? AND surah=? AND riwaya=?", (uid, surah, riwaya)).fetchone()
    con.close()
    return row[0] if row else 1

def log_tasbih(uid, phrase, count):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO tasbih_log (user_id, log_date, phrase, count) VALUES (?,?,?,?) ON CONFLICT(user_id, log_date, phrase) DO UPDATE SET count=count+excluded.count", (uid, date.today().isoformat(), phrase, count))
    con.commit(); con.close()

def get_tasbih_stats(uid):
    con  = sqlite3.connect(DB_PATH)
    rows = con.execute("SELECT phrase, SUM(count) as total FROM tasbih_log WHERE user_id=? GROUP BY phrase ORDER BY total DESC LIMIT 5", (uid,)).fetchall()
    total = con.execute("SELECT SUM(count) FROM tasbih_log WHERE user_id=?", (uid,)).fetchone()[0] or 0
    con.close(); return total, rows

def save_tasbih_session(uid, phrase_idx, counter):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO tasbih_session (user_id, phrase_idx, counter) VALUES (?,?,?) ON CONFLICT(user_id) DO UPDATE SET phrase_idx=excluded.phrase_idx, counter=excluded.counter", (uid, phrase_idx, counter))
    con.commit(); con.close()

def get_tasbih_session(uid):
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT phrase_idx, counter FROM tasbih_session WHERE user_id=?", (uid,)).fetchone()
    con.close()
    return (row[0], row[1]) if row else (0, 0)

def reset_tasbih_session(uid):
    con = sqlite3.connect(DB_PATH)
    con.execute("DELETE FROM tasbih_session WHERE user_id=?", (uid,))
    con.commit(); con.close()

def save_adhkar_progress(uid, key, idx):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO adhkar_progress (user_id, adhkar_key, idx, done_date) VALUES (?,?,?,?) ON CONFLICT(user_id, adhkar_key) DO UPDATE SET idx=excluded.idx, done_date=excluded.done_date", (uid, key, idx, date.today().isoformat()))
    con.commit(); con.close()

def get_adhkar_progress(uid, key):
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT idx, done_date FROM adhkar_progress WHERE user_id=? AND adhkar_key=?", (uid, key)).fetchone()
    con.close()
    if row and row[1] == date.today().isoformat(): return row[0]
    return 0

def reset_adhkar_progress(uid, key):
    con = sqlite3.connect(DB_PATH)
    con.execute("DELETE FROM adhkar_progress WHERE user_id=? AND adhkar_key=?", (uid, key))
    con.commit(); con.close()

def log_activity(uid, action, detail=""):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO activities (user_id, action, detail) VALUES (?,?,?)", (uid, action, detail))
    con.commit(); con.close()

def get_user_full_stats(uid):
    con = sqlite3.connect(DB_PATH)
    surah, ayah  = get_wird_progress(uid)
    total_t, tsb = get_tasbih_stats(uid)
    inquiries_cnt = con.execute("SELECT COUNT(*) FROM inquiries WHERE user_id=?", (uid,)).fetchone()[0]
    surahs_done   = con.execute("SELECT COUNT(DISTINCT surah) FROM surah_progress WHERE user_id=? AND last_ayah > 0", (uid,)).fetchone()[0]
    con.close()
    return {"wird_surah": surah, "wird_ayah": ayah, "total_t": total_t, "tasbih": tsb, "inquiries": inquiries_cnt, "surahs_done": surahs_done}

def get_all_users():
    con  = sqlite3.connect(DB_PATH)
    rows = con.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()
    con.close(); return [r[0] for r in rows]

def get_all_admins():
    con  = sqlite3.connect(DB_PATH)
    rows = con.execute("SELECT user_id FROM users WHERE is_admin=1").fetchall()
    con.close()
    admins = [r[0] for r in rows]
    admins += [a for a in SUPER_ADMINS if a not in admins]
    return list(set(admins))

def save_inquiry(uid, username, first_name, message):
    con = sqlite3.connect(DB_PATH)
    cur = con.execute("INSERT INTO inquiries (user_id, username, first_name, message) VALUES (?,?,?,?)", (uid, username, first_name, message))
    iid = cur.lastrowid; con.commit(); con.close(); return iid

def get_pending_inquiries():
    con  = sqlite3.connect(DB_PATH)
    rows = con.execute("SELECT id, user_id, username, first_name, message, created_at FROM inquiries WHERE status='pending' ORDER BY created_at DESC").fetchall()
    con.close(); return rows

def get_all_inquiries(limit=20):
    con  = sqlite3.connect(DB_PATH)
    rows = con.execute("SELECT id, user_id, username, first_name, message, status, created_at FROM inquiries ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    con.close(); return rows

def reply_to_inquiry(iid, reply_text):
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT user_id FROM inquiries WHERE id=?", (iid,)).fetchone()
    con.execute("UPDATE inquiries SET reply=?, status='replied', replied_at=CURRENT_TIMESTAMP WHERE id=?", (reply_text, iid))
    con.commit(); con.close()
    return row[0] if row else None

def save_user_city(uid, city):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO prayer_cities (user_id, city) VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET city=excluded.city", (uid, city))
    con.commit(); con.close()

def get_user_city(uid):
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT city FROM prayer_cities WHERE user_id=?", (uid,)).fetchone()
    con.close(); return row[0] if row else None

def ban_user(uid):
    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (uid,))
    con.commit(); con.close()

def unban_user(uid):
    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (uid,))
    con.commit(); con.close()

def mark_notif_sent(uid, key):
    con = sqlite3.connect(DB_PATH)
    try:
        con.execute("INSERT INTO notifications_sent (user_id, notif_key, sent_date) VALUES (?,?,?)", (uid, key, date.today().isoformat()))
        con.commit()
    except: pass
    con.close()

def notif_already_sent(uid, key):
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT 1 FROM notifications_sent WHERE user_id=? AND notif_key=? AND sent_date=?", (uid, key, date.today().isoformat())).fetchone()
    con.close(); return bool(row)

def get_admin_stats():
    con = sqlite3.connect(DB_PATH)
    today = date.today().isoformat()
    stats = {
        "users":        con.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "admins":       con.execute("SELECT COUNT(*) FROM users WHERE is_admin=1").fetchone()[0],
        "banned":       con.execute("SELECT COUNT(*) FROM users WHERE is_banned=1").fetchone()[0],
        "active_today": con.execute("SELECT COUNT(DISTINCT user_id) FROM activities WHERE DATE(created_at)=?", (today,)).fetchone()[0],
        "hadiths":      con.execute("SELECT COUNT(*) FROM hadiths").fetchone()[0],
        "duas":         con.execute("SELECT COUNT(*) FROM duas").fetchone()[0],
        "tasbih_total": con.execute("SELECT SUM(count) FROM tasbih_log").fetchone()[0] or 0,
        "pending":      con.execute("SELECT COUNT(*) FROM inquiries WHERE status='pending'").fetchone()[0],
        "replied":      con.execute("SELECT COUNT(*) FROM inquiries WHERE status='replied'").fetchone()[0],
        "content":      con.execute("SELECT COUNT(*) FROM bot_content").fetchone()[0],
    }
    con.close(); return stats

def get_users_list(limit=30):
    con  = sqlite3.connect(DB_PATH)
    rows = con.execute("SELECT user_id, username, first_name, is_admin, is_banned, last_seen FROM users ORDER BY last_seen DESC LIMIT ?", (limit,)).fetchall()
    con.close(); return rows

def delete_admin(uid):
    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE users SET is_admin=0 WHERE user_id=?", (uid,))
    con.commit(); con.close()

def add_custom_button(section, label, content, added_by):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO custom_buttons (section, btn_label, btn_content, added_by) VALUES (?,?,?,?)", (section, label, content, added_by))
    con.commit(); con.close()

def get_custom_buttons(section):
    con  = sqlite3.connect(DB_PATH)
    rows = con.execute("SELECT id, btn_label, btn_content FROM custom_buttons WHERE section=? ORDER BY added_at", (section,)).fetchall()
    con.close(); return rows

def get_all_custom_buttons():
    con  = sqlite3.connect(DB_PATH)
    rows = con.execute("SELECT id, section, btn_label, btn_content FROM custom_buttons ORDER BY section, added_at").fetchall()
    con.close(); return rows

def delete_custom_button(btn_id):
    con = sqlite3.connect(DB_PATH)
    con.execute("DELETE FROM custom_buttons WHERE id=?", (btn_id,))
    con.commit(); con.close()

def get_button_by_id(btn_id):
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT id, section, btn_label, btn_content FROM custom_buttons WHERE id=?", (btn_id,)).fetchone()
    con.close(); return row

# ══════════════════════════════════════════════════════════════════
# API HELPERS
# ══════════════════════════════════════════════════════════════════
async def fetch_dates():
    try:
        today    = date.today().strftime("%d-%m-%Y")
        now      = datetime.now()
        days_ar  = ["الاثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","السبت","الأحد"]
        day_name = days_ar[now.weekday()]
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as s:
            async with s.get(f"{ALADHAN_API}/gToH/{today}") as r:
                data = await r.json()
                h = data["data"]["hijri"]
                hijri = f"{h['day']} {h['month']['ar']} {h['year']} هـ"
        return f"📅 التاريخ الهجري: {hijri}\n📆 التاريخ الميلادي: {now.strftime('%A, %d %B %Y')}\n🌙 اليوم: {day_name}"
    except:
        return f"📆 التاريخ الميلادي: {datetime.now().strftime('%A, %d %B %Y')}"

async def fetch_prayer_times(city):
    try:
        today = date.today().strftime("%d-%m-%Y")
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(f"{ALADHAN_API}/timingsByCity/{today}", params={"city": city, "country": "DZ", "method": 3}) as r:
                data = await r.json()
        if data.get("code") != 200:
            return "⚠️ تعذّر جلب أوقات الصلاة."
        t = data["data"]["timings"]
        prayers = [("🌅 الفجر",t.get("Fajr","—")),("☀️ الشروق",t.get("Sunrise","—")),("🌤 الظهر",t.get("Dhuhr","—")),("🌇 العصر",t.get("Asr","—")),("🌆 المغرب",t.get("Maghrib","—")),("🌃 العشاء",t.get("Isha","—"))]
        lines = "\n".join([f"{n}: `{v}`" for n,v in prayers])
        return f"*🕌 أوقات الصلاة — {city}*\n\n{lines}\n\n_المصدر: aladhan.com_"
    except Exception as e:
        return f"⚠️ خطأ: {e}"

async def fetch_quran_ayah(surah, ayah, riwaya="hafs"):
    edition = "quran-uthmani" if riwaya == "hafs" else "quran-warsh-muujawwad"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as s:
            async with s.get(f"{QURAN_API}/ayah/{surah}:{ayah}/{edition}") as r:
                data = await r.json()
                if data.get("status") == "OK":
                    return data["data"]["text"]
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as s:
            async with s.get(f"{QURAN_API}/ayah/{surah}:{ayah}/quran-uthmani") as r:
                data = await r.json()
                return data["data"]["text"]
    except:
        return ""

# ══════════════════════════════════════════════════════════════════
# HELPERS & KEYBOARDS
# ══════════════════════════════════════════════════════════════════
def banned_check(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id if update.effective_user else None
        if uid and is_banned(uid): return
        return await func(update, context)
    return wrapper

async def safe_edit(query, text, reply_markup=None, parse_mode=ParseMode.MARKDOWN):
    try:
        await query.message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception:
        try:
            await query.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
        except Exception:
            pass

def back_btn(target="main_menu"):
    return InlineKeyboardButton("🔙 رجوع", callback_data=target)

def get_main_keyboard(uid=None):
    rows = [
        ["📖 القرآن الكريم",     "🌿 الورد اليومي"],
        ["📿 التسبيح",           "🌅 أذكار الصباح"],
        ["🌆 أذكار المساء",      "🌙 أذكار النوم"],
        ["🕌 أذكار الصلاة",     "🌺 أذكار الاستيقاظ"],
        ["💧 أذكار الوضوء",     "🌺 أدعية خاصة"],
        ["🌸 أحكام المرأة",      "⭐ سنن يوم الجمعة"],
        ["🕐 أوقات الصلاة",     "📅 التاريخ اليوم"],
        ["📚 حديث اليوم",        "🤲 دعاء اليوم"],
        ["🎓 الدورات المجانية", "📊 إحصائياتي"],
        ["💬 استفسار",           "ℹ️ المساعدة"],
    ]
    if uid and is_admin(uid):
        rows.append(["⚙️ لوحة الإدارة"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def build_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 الاستفسارات المعلقة", callback_data="adm_inquiries"),
         InlineKeyboardButton("📜 كل الاستفسارات",    callback_data="adm_all_inquiries")],
        [InlineKeyboardButton("➕ إضافة حديث",  callback_data="adm_add_hadith"),
         InlineKeyboardButton("🗑 حذف حديث",    callback_data="adm_del_hadith")],
        [InlineKeyboardButton("➕ إضافة دعاء",  callback_data="adm_add_dua"),
         InlineKeyboardButton("🗑 حذف دعاء",    callback_data="adm_del_dua")],
        [InlineKeyboardButton("➕ إضافة محتوى", callback_data="adm_add_content"),
         InlineKeyboardButton("🗑 حذف محتوى",   callback_data="adm_del_content")],
        [InlineKeyboardButton("👤 إضافة مشرف",  callback_data="adm_add_admin"),
         InlineKeyboardButton("❌ حذف مشرف",    callback_data="adm_del_admin")],
        [InlineKeyboardButton("🚫 حظر مستخدم",  callback_data="adm_ban"),
         InlineKeyboardButton("✅ رفع الحظر",   callback_data="adm_unban")],
        [InlineKeyboardButton("📩 إرسال لمستخدم", callback_data="adm_send_user"),
         InlineKeyboardButton("📢 بث عام",        callback_data="adm_broadcast")],
        [InlineKeyboardButton("👥 قائمة المستخدمين", callback_data="adm_users_list")],
        [InlineKeyboardButton("📊 إحصائيات البوت",   callback_data="adm_stats")],
        [InlineKeyboardButton("🔘 إدارة الأزرار المخصصة", callback_data="adm_custom_btns")],
        [InlineKeyboardButton("🔙 رجوع للقائمة",     callback_data="main_menu")],
    ])

def build_quran_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 رواية حفص عن عاصم", callback_data="sp_0_hafs")],
        [InlineKeyboardButton("📖 رواية ورش عن نافع",  callback_data="sp_0_warsh")],
        [InlineKeyboardButton("🎲 آية عشوائية",         callback_data="quran_random")],
        [back_btn("main_menu")],
    ])

def build_surah_keyboard(page, riwaya):
    surahs = list(SURAH_NAMES.items())
    per    = 20
    start  = page * per
    end    = min(start + per, 114)
    rows   = []
    chunk  = surahs[start:end]
    for i in range(0, len(chunk), 4):
        row = [InlineKeyboardButton(f"{num}. {name}", callback_data=f"ss_{num}_{riwaya}") for num, name in chunk[i:i+4]]
        rows.append(row)
    nav = []
    if page > 0:  nav.append(InlineKeyboardButton("◀️ السابق", callback_data=f"sp_{page-1}_{riwaya}"))
    if end < 114: nav.append(InlineKeyboardButton("التالي ▶️", callback_data=f"sp_{page+1}_{riwaya}"))
    if nav: rows.append(nav)
    rows.append([back_btn("quran_menu")])
    return InlineKeyboardMarkup(rows)

SECTIONS = {
    "main_menu":       "القائمة الرئيسية",
    "quran_menu":      "القرآن الكريم",
    "morning_adhkar":  "أذكار الصباح",
    "evening_adhkar":  "أذكار المساء",
    "sleep_adhkar":    "أذكار النوم",
    "wakeup_adhkar":   "أذكار الاستيقاظ",
    "wudu_adhkar":     "أذكار الوضوء",
    "prayer_adhkar":   "أذكار الصلاة",
    "special_duas":    "أدعية خاصة",
    "woman_adhkar":    "أحكام المرأة",
    "friday_sunnan":   "سنن يوم الجمعة",
    "tasbih_menu":     "التسبيح",
    "wird_menu":       "الورد اليومي",
}

# ══════════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ══════════════════════════════════════════════════════════════════
@banned_check
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    upsert_user(u.id, u.username, u.first_name, u.last_name)
    log_activity(u.id, "start")
    context.user_data.clear()
    await update.message.reply_text(
        f"بسم الله الرحمن الرحيم\n\nأهلاً وسهلاً {u.first_name} 🌙\n\nمرحباً بك في بوت المسلم الشامل.\nاختر ما تريد من القائمة أدناه:",
        reply_markup=get_main_keyboard(u.id)
    )

@banned_check
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    upsert_user(u.id, u.username, u.first_name, u.last_name)
    context.user_data.clear()
    text = (
        "ℹ️ *المساعدة*\n\n"
        "📖 *القرآن الكريم* — تصفح سور القرآن برواية حفص أو ورش\n"
        "🌿 *الورد اليومي* — تتبع ختمتك يوماً بيوم\n"
        "📿 *التسبيح* — عداد تسبيح مع حفظ الجلسة\n"
        "🌅 *أذكار الصباح والمساء* — بعداد تفاعلي\n"
        "🕌 *أذكار الصلاة* — أذكار مفصّلة\n"
        "🕐 *أوقات الصلاة* — لمدن الجزائر\n"
        "💬 *استفسار* — أرسل سؤالك للإدارة\n\n"
        "للعودة للقائمة في أي وقت اضغط /start"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(u.id))

# ══════════════════════════════════════════════════════════════════
# SECTION DISPLAY FUNCTIONS
# ══════════════════════════════════════════════════════════════════
async def show_wird(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    surah, ayah = get_wird_progress(u.id)
    if ayah < 1: ayah = 1
    total = SURAH_AYAH_COUNT.get(surah, 1)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 ابدأ القراءة", callback_data=f"wird_read_{surah}_{ayah}_hafs")],
        [InlineKeyboardButton("📖 ورش",          callback_data=f"wird_read_{surah}_{ayah}_warsh")],
        [InlineKeyboardButton("🔄 إعادة من البداية", callback_data="wird_reset")],
    ])
    await update.message.reply_text(
        f"🌿 *الورد اليومي*\n\n"
        f"📍 موضعك الحالي:\n"
        f"سورة *{SURAH_NAMES.get(surah, surah)}* — الآية *{ayah}* من *{total}*\n\n"
        f"اضغط للمتابعة من حيث توقفت:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )

async def show_tasbih(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    phrase_idx, counter = get_tasbih_session(u.id)
    if phrase_idx >= len(TASBIH_LIST): phrase_idx = 0
    phrase, fadl, target = TASBIH_LIST[phrase_idx]
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📿 سبّح ({counter}/{target})", callback_data=f"tsb_tap_{phrase_idx}_{counter}")],
        [InlineKeyboardButton("⏭ التسبيحة التالية", callback_data=f"tsb_next_{phrase_idx}"),
         InlineKeyboardButton("⏮ السابقة",          callback_data=f"tsb_prev_{phrase_idx}")],
        [InlineKeyboardButton("🔄 إعادة العداد", callback_data=f"tsb_reset_{phrase_idx}"),
         InlineKeyboardButton("📊 إحصائياتي",   callback_data="tsb_stats")],
    ])
    await update.message.reply_text(
        f"📿 *التسبيح*\n\n"
        f"*{phrase}*\n\n"
        f"💡 {fadl}\n\n"
        f"العداد: *{counter} / {target}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )

async def show_adhkar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str, title: str, adhkar_list: list):
    u   = update.effective_user
    idx = get_adhkar_progress(u.id, key)
    if idx >= len(adhkar_list): idx = 0
    text_a, source, times = adhkar_list[idx]
    total = len(adhkar_list)
    nav = []
    if idx > 0:       nav.append(InlineKeyboardButton("◀️ السابق", callback_data=f"adhk_{key}_{idx-1}"))
    if idx < total-1: nav.append(InlineKeyboardButton("التالي ▶️", callback_data=f"adhk_{key}_{idx+1}"))
    kb_rows = []
    if nav: kb_rows.append(nav)
    kb_rows.append([InlineKeyboardButton("🔄 إعادة من البداية", callback_data=f"adhk_reset_{key}")])
    kb_rows.append([back_btn("main_menu")])
    msg = (
        f"{title}\n\n"
        f"📿 *الذكر {idx+1} من {total}:*\n\n"
        f"{text_a}\n\n"
        f"🔢 _{source}_"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb_rows))

async def show_prayer_adhkar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keys = list(PRAYER_ADHKAR.keys())
    kb_rows = [[InlineKeyboardButton(k, callback_data=f"pradh_{i}")] for i, k in enumerate(keys)]
    kb_rows.append([back_btn("main_menu")])
    await update.message.reply_text("🕌 *أذكار الصلاة*\nاختر القسم:", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb_rows))

async def show_special_duas_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keys = list(SPECIAL_DUAS.keys())
    kb_rows = [[InlineKeyboardButton(k, callback_data=f"sd_{i}")] for i, k in enumerate(keys)]
    kb_rows.append([back_btn("main_menu")])
    await update.message.reply_text("🌺 *أدعية خاصة*\nاختر الدعاء:", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb_rows))

async def show_woman_adhkar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keys = list(WOMAN_ADHKAR.keys())
    kb_rows = [[InlineKeyboardButton(k, callback_data=f"wom_{i}")] for i, k in enumerate(keys)]
    kb_rows.append([back_btn("main_menu")])
    await update.message.reply_text("🌸 *أحكام المرأة والأدعية*\nاختر القسم:", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb_rows))

async def show_friday_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb_rows = [[InlineKeyboardButton(s["title"], callback_data=f"fri_{i}")] for i, s in enumerate(FRIDAY_SUNNAN)]
    kb_rows.append([InlineKeyboardButton("📖 سور الجمعة", callback_data="fri_surahs")])
    kb_rows.append([back_btn("main_menu")])
    await update.message.reply_text("⭐ *سنن يوم الجمعة*\nاختر:", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb_rows))

# ══════════════════════════════════════════════════════════════════
# MESSAGE HANDLER (Reply Keyboard)
# ══════════════════════════════════════════════════════════════════
@banned_check
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u    = update.effective_user
    text = update.message.text.strip()
    upsert_user(u.id, u.username, u.first_name, u.last_name)

    # ── Admin conversation states ──────────────────────────────────
    state = context.user_data.get("state")

    if state == "await_hadith":
        parts = text.split("|", 1)
        if len(parts) == 2:
            con = sqlite3.connect(DB_PATH)
            con.execute("INSERT INTO hadiths (text, source, added_by) VALUES (?,?,?)", (parts[0].strip(), parts[1].strip(), u.id))
            con.commit(); con.close()
            context.user_data.clear()
            await update.message.reply_text("✅ تم إضافة الحديث.", reply_markup=get_main_keyboard(u.id))
        else:
            await update.message.reply_text("⚠️ الصيغة غير صحيحة. أرسل: نص الحديث | المصدر")
        return

    if state == "await_dua":
        parts = text.split("|", 1)
        if len(parts) == 2:
            con = sqlite3.connect(DB_PATH)
            con.execute("INSERT INTO duas (text, source, added_by) VALUES (?,?,?)", (parts[0].strip(), parts[1].strip(), u.id))
            con.commit(); con.close()
            context.user_data.clear()
            await update.message.reply_text("✅ تم إضافة الدعاء.", reply_markup=get_main_keyboard(u.id))
        else:
            await update.message.reply_text("⚠️ الصيغة غير صحيحة. أرسل: نص الدعاء | المصدر")
        return

    if state == "await_content":
        parts = text.split("|", 2)
        if len(parts) == 3:
            con = sqlite3.connect(DB_PATH)
            con.execute("INSERT INTO bot_content (category, text, source, added_by) VALUES (?,?,?,?)", (parts[0].strip(), parts[1].strip(), parts[2].strip(), u.id))
            con.commit(); con.close()
            context.user_data.clear()
            await update.message.reply_text("✅ تم إضافة المحتوى.", reply_markup=get_main_keyboard(u.id))
        else:
            await update.message.reply_text("⚠️ الصيغة: الفئة | النص | المصدر")
        return

    if state == "await_add_admin":
        try:
            new_uid = int(text.strip())
            con = sqlite3.connect(DB_PATH)
            con.execute("INSERT INTO users (user_id, username, first_name, is_admin) VALUES (?,?,?,1) ON CONFLICT(user_id) DO UPDATE SET is_admin=1", (new_uid, "", "مشرف"))
            con.commit(); con.close()
            context.user_data.clear()
            await update.message.reply_text(f"✅ تم تعيين {new_uid} مشرفاً.", reply_markup=get_main_keyboard(u.id))
        except ValueError:
            await update.message.reply_text("⚠️ أرسل معرف المستخدم رقمياً.")
        return

    if state == "await_del_admin":
        try:
            del_uid = int(text.strip())
            if del_uid in SUPER_ADMINS:
                await update.message.reply_text("⚠️ لا يمكن حذف المشرف الرئيسي.")
            else:
                delete_admin(del_uid)
                context.user_data.clear()
                await update.message.reply_text(f"✅ تم إزالة صلاحيات {del_uid}.", reply_markup=get_main_keyboard(u.id))
        except ValueError:
            await update.message.reply_text("⚠️ أرسل معرف المستخدم رقمياً.")
        return

    if state == "await_ban":
        try:
            ban_uid = int(text.strip())
            if ban_uid in SUPER_ADMINS:
                await update.message.reply_text("⚠️ لا يمكن حظر مشرف رئيسي.")
            else:
                ban_user(ban_uid)
                context.user_data.clear()
                await update.message.reply_text(f"✅ تم حظر المستخدم {ban_uid}.", reply_markup=get_main_keyboard(u.id))
        except ValueError:
            await update.message.reply_text("⚠️ أرسل معرف المستخدم رقمياً.")
        return

    if state == "await_unban":
        try:
            unban_uid = int(text.strip())
            unban_user(unban_uid)
            context.user_data.clear()
            await update.message.reply_text(f"✅ تم رفع الحظر عن {unban_uid}.", reply_markup=get_main_keyboard(u.id))
        except ValueError:
            await update.message.reply_text("⚠️ أرسل معرف المستخدم رقمياً.")
        return

    if state == "await_broadcast":
        sent = 0
        for uid in get_all_users():
            try:
                await context.bot.send_message(uid, text)
                sent += 1
            except Exception:
                pass
        context.user_data.clear()
        await update.message.reply_text(f"✅ تم الإرسال لـ {sent} مستخدم.", reply_markup=get_main_keyboard(u.id))
        return

    if state == "await_send_user":
        target_uid = context.user_data.get("send_target")
        if target_uid:
            try:
                await context.bot.send_message(target_uid, text)
                context.user_data.clear()
                await update.message.reply_text("✅ تم الإرسال.", reply_markup=get_main_keyboard(u.id))
            except Exception as e:
                await update.message.reply_text(f"⚠️ فشل الإرسال: {e}")
        return

    if state == "await_send_user_id":
        try:
            target_uid = int(text.strip())
            context.user_data["send_target"] = target_uid
            context.user_data["state"] = "await_send_user"
            await update.message.reply_text(f"✏️ أرسل الآن الرسالة لـ {target_uid}:")
        except ValueError:
            await update.message.reply_text("⚠️ أرسل معرف رقمياً.")
        return

    if state == "await_reply_id":
        try:
            iid = int(text.strip())
            context.user_data["reply_iid"] = iid
            context.user_data["state"]     = "await_reply_text"
            await update.message.reply_text(f"✏️ أرسل الرد على الاستفسار #{iid}:")
        except ValueError:
            await update.message.reply_text("⚠️ أرسل رقم الاستفسار.")
        return

    if state == "await_reply_text":
        iid = context.user_data.get("reply_iid")
        if iid:
            user_id = reply_to_inquiry(iid, text)
            if user_id:
                try:
                    await context.bot.send_message(user_id, f"📩 *رد على استفسارك:*\n\n{text}", parse_mode=ParseMode.MARKDOWN)
                except Exception:
                    pass
            context.user_data.clear()
            await update.message.reply_text("✅ تم الرد.", reply_markup=get_main_keyboard(u.id))
        return

    if state == "await_del_hadith_id":
        try:
            hid = int(text.strip())
            con = sqlite3.connect(DB_PATH)
            con.execute("DELETE FROM hadiths WHERE id=?", (hid,))
            con.commit(); con.close()
            context.user_data.clear()
            await update.message.reply_text(f"✅ تم حذف الحديث #{hid}.", reply_markup=get_main_keyboard(u.id))
        except ValueError:
            await update.message.reply_text("⚠️ أرسل رقم الحديث.")
        return

    if state == "await_del_dua_id":
        try:
            did = int(text.strip())
            con = sqlite3.connect(DB_PATH)
            con.execute("DELETE FROM duas WHERE id=?", (did,))
            con.commit(); con.close()
            context.user_data.clear()
            await update.message.reply_text(f"✅ تم حذف الدعاء #{did}.", reply_markup=get_main_keyboard(u.id))
        except ValueError:
            await update.message.reply_text("⚠️ أرسل رقم الدعاء.")
        return

    if state == "await_del_content_id":
        try:
            cid = int(text.strip())
            con = sqlite3.connect(DB_PATH)
            con.execute("DELETE FROM bot_content WHERE id=?", (cid,))
            con.commit(); con.close()
            context.user_data.clear()
            await update.message.reply_text(f"✅ تم حذف المحتوى #{cid}.", reply_markup=get_main_keyboard(u.id))
        except ValueError:
            await update.message.reply_text("⚠️ أرسل رقم المحتوى.")
        return

    if state == "await_custom_btn":
        parts = text.split("|", 2)
        if len(parts) == 3:
            section, label, content = parts[0].strip(), parts[1].strip(), parts[2].strip()
            add_custom_button(section, label, content, u.id)
            context.user_data.clear()
            await update.message.reply_text("✅ تم إضافة الزر المخصص.", reply_markup=get_main_keyboard(u.id))
        else:
            await update.message.reply_text("⚠️ الصيغة: القسم | اسم الزر | المحتوى")
        return

    if state == "await_city":
        city = text.strip()
        if city in ALGERIAN_CITIES:
            save_user_city(u.id, city)
            context.user_data.clear()
            pt = await fetch_prayer_times(city)
            await update.message.reply_text(pt, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(u.id))
        else:
            cities_text = "\n".join(ALGERIAN_CITIES)
            await update.message.reply_text(f"⚠️ المدينة غير موجودة. اختر من القائمة:\n\n{cities_text}")
        return

    if state == "await_inquiry":
        iid = save_inquiry(u.id, u.username, u.first_name, text)
        context.user_data.clear()
        await update.message.reply_text(f"✅ تم إرسال استفسارك (#{iid}). سيرد عليك المشرف قريباً إن شاء الله.", reply_markup=get_main_keyboard(u.id))
        for admin_id in get_all_admins():
            try:
                await context.bot.send_message(
                    admin_id,
                    f"📩 *استفسار جديد #{iid}*\n👤 {u.first_name} (@{u.username or 'لا يوجد'}) | ID: `{u.id}`\n\n{text}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass
        return

    # ── Main keyboard routing ──────────────────────────────────────
    log_activity(u.id, "menu", text)
    context.user_data.clear()

    if text == "📖 القرآن الكريم":
        await update.message.reply_text("📖 *القرآن الكريم*\nاختر الرواية:", parse_mode=ParseMode.MARKDOWN, reply_markup=build_quran_keyboard())

    elif text == "🌿 الورد اليومي":
        await show_wird(update, context)

    elif text == "📿 التسبيح":
        await show_tasbih(update, context)

    elif text == "🌅 أذكار الصباح":
        await show_adhkar_menu(update, context, "morning", "🌅 *أذكار الصباح*", MORNING_ADHKAR)

    elif text == "🌆 أذكار المساء":
        await show_adhkar_menu(update, context, "evening", "🌆 *أذكار المساء*", EVENING_ADHKAR)

    elif text == "🌙 أذكار النوم":
        await show_adhkar_menu(update, context, "sleep", "🌙 *أذكار النوم*", SLEEP_ADHKAR)

    elif text == "🌺 أذكار الاستيقاظ":
        await show_adhkar_menu(update, context, "wakeup", "🌺 *أذكار الاستيقاظ*", WAKEUP_ADHKAR)

    elif text == "💧 أذكار الوضوء":
        await show_adhkar_menu(update, context, "wudu", "💧 *أذكار الوضوء*", WUDU_ADHKAR)

    elif text == "🕌 أذكار الصلاة":
        await show_prayer_adhkar_menu(update, context)

    elif text == "🌺 أدعية خاصة":
        await show_special_duas_menu(update, context)

    elif text == "🌸 أحكام المرأة":
        await show_woman_adhkar_menu(update, context)

    elif text == "⭐ سنن يوم الجمعة":
        await show_friday_menu(update, context)

    elif text == "🕐 أوقات الصلاة":
        city = get_user_city(u.id)
        if city:
            pt = await fetch_prayer_times(city)
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 تغيير المدينة", callback_data="change_city")]])
            await update.message.reply_text(pt, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        else:
            context.user_data["state"] = "await_city"
            cities_text = "\n".join(ALGERIAN_CITIES)
            await update.message.reply_text(f"🏙️ أرسل اسم مدينتك:\n\n{cities_text}")

    elif text == "📅 التاريخ اليوم":
        dt = await fetch_dates()
        await update.message.reply_text(dt)

    elif text == "📚 حديث اليوم":
        row = get_random_hadith()
        if row:
            await update.message.reply_text(f"📚 *حديث اليوم*\n\n{row[0]}\n\n📖 _{row[1]}_", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("⚠️ لا توجد أحاديث مضافة بعد.")

    elif text == "🤲 دعاء اليوم":
        row = get_random_dua()
        if row:
            await update.message.reply_text(f"🤲 *دعاء اليوم*\n\n{row[0]}\n\n📖 _{row[1]}_", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("⚠️ لا توجد أدعية مضافة بعد.")

    elif text == "🎓 الدورات المجانية":
        courses = get_custom_buttons("courses")
        if courses:
            kb = [[InlineKeyboardButton(c[1], callback_data=f"custbtn_{c[0]}")] for c in courses]
            await update.message.reply_text("🎓 *الدورات المجانية:*", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb))
        else:
            await update.message.reply_text("⚠️ لا توجد دورات مضافة حالياً. تابع البوت للمستجدات.")

    elif text == "📊 إحصائياتي":
        s = get_user_full_stats(u.id)
        sname = SURAH_NAMES.get(s["wird_surah"], s["wird_surah"])
        lines = f"📊 *إحصائياتك*\n\n📖 الورد: سورة {sname} آية {s['wird_ayah']}\n📿 إجمالي التسبيح: {s['total_t']}\n📚 السور المكتملة: {s['surahs_done']}\n💬 الاستفسارات: {s['inquiries']}"
        await update.message.reply_text(lines, parse_mode=ParseMode.MARKDOWN)

    elif text == "💬 استفسار":
        context.user_data["state"] = "await_inquiry"
        await update.message.reply_text("✏️ أرسل استفسارك وسيُحال للمشرف:")

    elif text == "ℹ️ المساعدة":
        await cmd_help(update, context)

    elif text == "⚙️ لوحة الإدارة":
        if not is_admin(u.id):
            await update.message.reply_text("⛔ ليس لديك صلاحية.")
            return
        stats = get_admin_stats()
        msg = (
            f"⚙️ *لوحة الإدارة*\n\n"
            f"👥 المستخدمون: {stats['users']}\n"
            f"🛡 المشرفون: {stats['admins']}\n"
            f"🚫 المحظورون: {stats['banned']}\n"
            f"✅ نشطون اليوم: {stats['active_today']}\n"
            f"📚 الأحاديث: {stats['hadiths']}\n"
            f"🤲 الأدعية: {stats['duas']}\n"
            f"📝 المحتوى: {stats['content']}\n"
            f"📿 مجموع التسبيح: {stats['tasbih_total']}\n"
            f"📋 معلق: {stats['pending']} | ✅ مُجاب: {stats['replied']}"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=build_admin_keyboard())

    else:
        await update.message.reply_text("اضغط /start للعودة للقائمة.")

# ══════════════════════════════════════════════════════════════════
# CALLBACK QUERY HANDLER
# ══════════════════════════════════════════════════════════════════
@banned_check
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data  = query.data
    u     = query.from_user
    uid   = u.id

    # ── Main menu ──────────────────────────────────────────────────
    if data == "main_menu":
        context.user_data.clear()
        await safe_edit(query, "اختر من القائمة الرئيسية:", reply_markup=InlineKeyboardMarkup([[back_btn("main_menu")]]))
        return

    if data == "quran_menu":
        await safe_edit(query, "📖 *القرآن الكريم*\nاختر الرواية:", parse_mode=ParseMode.MARKDOWN, reply_markup=build_quran_keyboard())
        return

    # ── Quran random ───────────────────────────────────────────────
    if data == "quran_random":
        s = random.randint(1, 114)
        a = random.randint(1, SURAH_AYAH_COUNT[s])
        txt = await fetch_quran_ayah(s, a)
        kb  = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 آية أخرى", callback_data="quran_random")],
            [back_btn("quran_menu")],
        ])
        await safe_edit(query, f"📖 *{SURAH_NAMES[s]}* — آية {a}\n\n{txt}", reply_markup=kb)
        return

    # ── Surah pages: sp_PAGE_RIWAYA ────────────────────────────────
    if data.startswith("sp_"):
        parts  = data.split("_", 2)   # ['sp', 'PAGE', 'RIWAYA']
        page   = int(parts[1])
        riwaya = parts[2]
        await safe_edit(query, f"📖 اختر السورة — رواية {'حفص' if riwaya=='hafs' else 'ورش'}:", reply_markup=build_surah_keyboard(page, riwaya))
        return

    # ── Select surah: ss_SURAH_RIWAYA ─────────────────────────────
    if data.startswith("ss_"):
        parts  = data.split("_", 2)
        surah  = int(parts[1])
        riwaya = parts[2]
        last   = get_surah_progress(uid, surah, riwaya)
        if last < 1: last = 1
        total  = SURAH_AYAH_COUNT[surah]
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ ابدأ من البداية",    callback_data=f"sq_{surah}_1_{riwaya}")],
            [InlineKeyboardButton(f"📍 متابعة من آية {last}", callback_data=f"sq_{surah}_{last}_{riwaya}")],
            [back_btn(f"sp_0_{riwaya}")],
        ])
        await safe_edit(query, f"📖 *{SURAH_NAMES[surah]}*\nعدد الآيات: {total}\nآخر موضع محفوظ: {last}", reply_markup=kb)
        return

    # ── Read ayah: sq_SURAH_AYAH_RIWAYA ───────────────────────────
    if data.startswith("sq_"):
        parts  = data.split("_", 3)
        surah  = int(parts[1])
        ayah   = int(parts[2])
        riwaya = parts[3]
        total  = SURAH_AYAH_COUNT[surah]
        txt    = await fetch_quran_ayah(surah, ayah, riwaya)
        save_surah_progress(uid, surah, ayah, riwaya)
        nav = []
        if ayah > 1:    nav.append(InlineKeyboardButton("◀️ السابقة", callback_data=f"sq_{surah}_{ayah-1}_{riwaya}"))
        if ayah < total:nav.append(InlineKeyboardButton("التالية ▶️", callback_data=f"sq_{surah}_{ayah+1}_{riwaya}"))
        kb_rows = []
        if nav: kb_rows.append(nav)
        # next surah
        if ayah == total and surah < 114:
            kb_rows.append([InlineKeyboardButton(f"▶️ السورة التالية: {SURAH_NAMES[surah+1]}", callback_data=f"ss_{surah+1}_{riwaya}")])
        kb_rows.append([back_btn(f"ss_{surah}_{riwaya}")])
        rname = "حفص" if riwaya == "hafs" else "ورش"
        await safe_edit(
            query,
            f"📖 *{SURAH_NAMES[surah]}* — آية {ayah}/{total} ({rname})\n\n{txt}",
            reply_markup=InlineKeyboardMarkup(kb_rows)
        )
        return

    # ── Wird read: wird_read_SURAH_AYAH_RIWAYA ────────────────────
    if data.startswith("wird_read_"):
        parts  = data.split("_")   # ['wird','read','SURAH','AYAH','RIWAYA']
        surah  = int(parts[2])
        ayah   = int(parts[3])
        riwaya = parts[4]
        total  = SURAH_AYAH_COUNT[surah]
        txt    = await fetch_quran_ayah(surah, ayah, riwaya)
        save_wird_progress(uid, surah, ayah)
        nav = []
        if ayah > 1:
            nav.append(InlineKeyboardButton("◀️ السابقة", callback_data=f"wird_read_{surah}_{ayah-1}_{riwaya}"))
        if ayah < total:
            nav.append(InlineKeyboardButton("التالية ▶️", callback_data=f"wird_read_{surah}_{ayah+1}_{riwaya}"))
        kb_rows = []
        if nav: kb_rows.append(nav)
        if ayah == total and surah < 114:
            next_surah = surah + 1
            kb_rows.append([InlineKeyboardButton(f"▶️ سورة {SURAH_NAMES[next_surah]}", callback_data=f"wird_read_{next_surah}_1_{riwaya}")])
            save_wird_progress(uid, next_surah, 1)
        rname = "حفص" if riwaya == "hafs" else "ورش"
        kb_rows.append([back_btn("main_menu")])
        await safe_edit(
            query,
            f"🌿 *الورد اليومي* — {SURAH_NAMES[surah]} آية {ayah}/{total} ({rname})\n\n{txt}",
            reply_markup=InlineKeyboardMarkup(kb_rows)
        )
        return

    if data == "wird_reset":
        save_wird_progress(uid, 2, 1)
        await safe_edit(query, "✅ تمت إعادة الورد من البداية — سورة البقرة آية 1.", reply_markup=InlineKeyboardMarkup([[back_btn("main_menu")]]))
        return

    # ── Tasbih tap: tsb_tap_IDX_COUNT ────────────────────────────
    if data.startswith("tsb_tap_"):
        parts = data.split("_")   # ['tsb','tap','IDX','COUNT']
        pidx  = int(parts[2])
        count = int(parts[3]) + 1
        if pidx >= len(TASBIH_LIST): pidx = 0
        phrase, fadl, target = TASBIH_LIST[pidx]
        save_tasbih_session(uid, pidx, count)
        if count >= target:
            log_tasbih(uid, phrase, count)
            reset_tasbih_session(uid)
            mot = random.choice(MOTIVATION_MSGS)
            kb  = InlineKeyboardMarkup([
                [InlineKeyboardButton("⏭ التسبيحة التالية", callback_data=f"tsb_next_{pidx}")],
                [InlineKeyboardButton("🔄 إعادة نفس التسبيحة", callback_data=f"tsb_restart_{pidx}")],
            ])
            await safe_edit(query, f"✅ *أتممت التسبيحة!*\n\n{phrase}\n\n{mot}", reply_markup=kb)
        else:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"📿 سبّح ({count}/{target})", callback_data=f"tsb_tap_{pidx}_{count}")],
                [InlineKeyboardButton("⏭ التالية", callback_data=f"tsb_next_{pidx}"),
                 InlineKeyboardButton("⏮ السابقة", callback_data=f"tsb_prev_{pidx}")],
                [InlineKeyboardButton("🔄 إعادة", callback_data=f"tsb_reset_{pidx}"),
                 InlineKeyboardButton("📊 إحصائياتي", callback_data="tsb_stats")],
            ])
            await safe_edit(query, f"📿 *{phrase}*\n\n💡 {fadl}\n\nالعداد: *{count} / {target}*", reply_markup=kb)
        return

    # ── Tasbih next: tsb_next_IDX ─────────────────────────────────
    if data.startswith("tsb_next_"):
        pidx  = (int(data.split("_")[2]) + 1) % len(TASBIH_LIST)
        phrase, fadl, target = TASBIH_LIST[pidx]
        save_tasbih_session(uid, pidx, 0)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📿 سبّح (0/{target})", callback_data=f"tsb_tap_{pidx}_0")],
            [InlineKeyboardButton("⏭ التالية", callback_data=f"tsb_next_{pidx}"),
             InlineKeyboardButton("⏮ السابقة", callback_data=f"tsb_prev_{pidx}")],
            [InlineKeyboardButton("🔄 إعادة",   callback_data=f"tsb_reset_{pidx}"),
             InlineKeyboardButton("📊 إحصائياتي", callback_data="tsb_stats")],
        ])
        await safe_edit(query, f"📿 *{phrase}*\n\n💡 {fadl}\n\nالعداد: *0 / {target}*", reply_markup=kb)
        return

    # ── Tasbih prev: tsb_prev_IDX ─────────────────────────────────
    if data.startswith("tsb_prev_"):
        pidx  = (int(data.split("_")[2]) - 1) % len(TASBIH_LIST)
        phrase, fadl, target = TASBIH_LIST[pidx]
        save_tasbih_session(uid, pidx, 0)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📿 سبّح (0/{target})", callback_data=f"tsb_tap_{pidx}_0")],
            [InlineKeyboardButton("⏭ التالية", callback_data=f"tsb_next_{pidx}"),
             InlineKeyboardButton("⏮ السابقة", callback_data=f"tsb_prev_{pidx}")],
            [InlineKeyboardButton("🔄 إعادة",   callback_data=f"tsb_reset_{pidx}"),
             InlineKeyboardButton("📊 إحصائياتي", callback_data="tsb_stats")],
        ])
        await safe_edit(query, f"📿 *{phrase}*\n\n💡 {fadl}\n\nالعداد: *0 / {target}*", reply_markup=kb)
        return

    # ── Tasbih reset: tsb_reset_IDX ───────────────────────────────
    if data.startswith("tsb_reset_"):
        pidx  = int(data.split("_")[2])
        if pidx >= len(TASBIH_LIST): pidx = 0
        phrase, fadl, target = TASBIH_LIST[pidx]
        save_tasbih_session(uid, pidx, 0)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📿 سبّح (0/{target})", callback_data=f"tsb_tap_{pidx}_0")],
            [InlineKeyboardButton("⏭ التالية", callback_data=f"tsb_next_{pidx}"),
             InlineKeyboardButton("⏮ السابقة", callback_data=f"tsb_prev_{pidx}")],
            [InlineKeyboardButton("📊 إحصائياتي", callback_data="tsb_stats")],
        ])
        await safe_edit(query, f"📿 *{phrase}*\n\n💡 {fadl}\n\nالعداد: *0 / {target}*", reply_markup=kb)
        return

    # ── Tasbih restart: tsb_restart_IDX ───────────────────────────
    if data.startswith("tsb_restart_"):
        pidx  = int(data.split("_")[2])
        if pidx >= len(TASBIH_LIST): pidx = 0
        phrase, fadl, target = TASBIH_LIST[pidx]
        save_tasbih_session(uid, pidx, 0)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📿 سبّح (0/{target})", callback_data=f"tsb_tap_{pidx}_0")],
            [InlineKeyboardButton("⏭ التالية", callback_data=f"tsb_next_{pidx}")],
        ])
        await safe_edit(query, f"📿 *{phrase}*\n\n💡 {fadl}\n\nالعداد: *0 / {target}*", reply_markup=kb)
        return

    # ── Tasbih stats ──────────────────────────────────────────────
    if data == "tsb_stats":
        total, rows = get_tasbih_stats(uid)
        lines = "\n".join([f"• {r[0]}: {r[1]}" for r in rows]) if rows else "لا توجد إحصائيات بعد."
        await safe_edit(query, f"📊 *إحصائيات التسبيح*\n\nالإجمالي: {total}\n\n{lines}", reply_markup=InlineKeyboardMarkup([[back_btn("main_menu")]]))
        return

    # ── Adhkar nav: adhk_KEY_IDX ──────────────────────────────────
    if data.startswith("adhk_") and not data.startswith("adhk_reset_"):
        parts = data.split("_", 2)   # ['adhk', 'KEY', 'IDX']
        key   = parts[1]
        idx   = int(parts[2])
        ADHKAR_MAP = {
            "morning": ("🌅 *أذكار الصباح*",    MORNING_ADHKAR),
            "evening": ("🌆 *أذكار المساء*",     EVENING_ADHKAR),
            "sleep":   ("🌙 *أذكار النوم*",      SLEEP_ADHKAR),
            "wakeup":  ("🌺 *أذكار الاستيقاظ*",  WAKEUP_ADHKAR),
            "wudu":    ("💧 *أذكار الوضوء*",     WUDU_ADHKAR),
        }
        if key not in ADHKAR_MAP:
            await query.answer("⚠️ مجموعة غير معروفة")
            return
        title, lst = ADHKAR_MAP[key]
        if idx < 0: idx = 0
        if idx >= len(lst): idx = len(lst) - 1
        save_adhkar_progress(uid, key, idx)
        text_a, source, times = lst[idx]
        total = len(lst)
        nav = []
        if idx > 0:       nav.append(InlineKeyboardButton("◀️ السابق", callback_data=f"adhk_{key}_{idx-1}"))
        if idx < total-1: nav.append(InlineKeyboardButton("التالي ▶️",  callback_data=f"adhk_{key}_{idx+1}"))
        kb_rows = []
        if nav: kb_rows.append(nav)
        kb_rows.append([InlineKeyboardButton("🔄 إعادة من البداية", callback_data=f"adhk_reset_{key}")])
        kb_rows.append([back_btn("main_menu")])
        msg = f"{title}\n\n📿 *الذكر {idx+1} من {total}:*\n\n{text_a}\n\n🔢 _{source}_"
        await safe_edit(query, msg, reply_markup=InlineKeyboardMarkup(kb_rows))
        return

    # ── Adhkar reset: adhk_reset_KEY ──────────────────────────────
    if data.startswith("adhk_reset_"):
        key = data[len("adhk_reset_"):]
        reset_adhkar_progress(uid, key)
        ADHKAR_MAP = {
            "morning": ("🌅 *أذكار الصباح*",    MORNING_ADHKAR),
            "evening": ("🌆 *أذكار المساء*",     EVENING_ADHKAR),
            "sleep":   ("🌙 *أذكار النوم*",      SLEEP_ADHKAR),
            "wakeup":  ("🌺 *أذكار الاستيقاظ*",  WAKEUP_ADHKAR),
            "wudu":    ("💧 *أذكار الوضوء*",     WUDU_ADHKAR),
        }
        if key not in ADHKAR_MAP:
            await query.answer("⚠️")
            return
        title, lst = ADHKAR_MAP[key]
        text_a, source, times = lst[0]
        total = len(lst)
        kb_rows = [
            [InlineKeyboardButton("التالي ▶️", callback_data=f"adhk_{key}_1")],
            [back_btn("main_menu")],
        ]
        await safe_edit(query, f"{title}\n\n📿 *الذكر 1 من {total}:*\n\n{text_a}\n\n🔢 _{source}_", reply_markup=InlineKeyboardMarkup(kb_rows))
        return

    # ── Prayer adhkar: pradh_IDX ──────────────────────────────────
    if data.startswith("pradh_"):
        idx  = int(data.split("_")[1])
        keys = list(PRAYER_ADHKAR.keys())
        if idx >= len(keys): return
        key_name = keys[idx]
        items    = PRAYER_ADHKAR[key_name]
        lines    = "\n\n".join([f"*{i+1}.* {item[0]}\n🔢 _{item[1]}_" for i, item in enumerate(items)])
        kb = InlineKeyboardMarkup([
            [back_btn("prayer_adhkar_menu")],
        ])
        await safe_edit(query, f"🕌 *{key_name}*\n\n{lines}", reply_markup=kb)
        return

    if data == "prayer_adhkar_menu":
        keys = list(PRAYER_ADHKAR.keys())
        kb_rows = [[InlineKeyboardButton(k, callback_data=f"pradh_{i}")] for i, k in enumerate(keys)]
        kb_rows.append([back_btn("main_menu")])
        await safe_edit(query, "🕌 *أذكار الصلاة*\nاختر القسم:", reply_markup=InlineKeyboardMarkup(kb_rows))
        return

    # ── Special duas: sd_IDX ──────────────────────────────────────
    if data.startswith("sd_"):
        idx  = int(data.split("_")[1])
        keys = list(SPECIAL_DUAS.keys())
        if idx >= len(keys): return
        key_name = keys[idx]
        items    = SPECIAL_DUAS[key_name]
        lines    = "\n\n".join([f"*{i+1}.* {item[0]}\n🔢 _{item[1]}_" for i, item in enumerate(items)])
        kb = InlineKeyboardMarkup([[back_btn("special_duas_menu")]])
        await safe_edit(query, f"🌺 *{key_name}*\n\n{lines}", reply_markup=kb)
        return

    if data == "special_duas_menu":
        keys = list(SPECIAL_DUAS.keys())
        kb_rows = [[InlineKeyboardButton(k, callback_data=f"sd_{i}")] for i, k in enumerate(keys)]
        kb_rows.append([back_btn("main_menu")])
        await safe_edit(query, "🌺 *أدعية خاصة*\nاختر الدعاء:", reply_markup=InlineKeyboardMarkup(kb_rows))
        return

    # ── Woman adhkar: wom_IDX ─────────────────────────────────────
    if data.startswith("wom_"):
        idx  = int(data.split("_")[1])
        keys = list(WOMAN_ADHKAR.keys())
        if idx >= len(keys): return
        key_name = keys[idx]
        items    = WOMAN_ADHKAR[key_name]
        lines    = "\n\n".join([f"*{i+1}.* {item[0]}\n🔢 _{item[1]}_" for i, item in enumerate(items)])
        kb = InlineKeyboardMarkup([[back_btn("woman_adhkar_menu")]])
        await safe_edit(query, f"🌸 *{key_name}*\n\n{lines}", reply_markup=kb)
        return

    if data == "woman_adhkar_menu":
        keys = list(WOMAN_ADHKAR.keys())
        kb_rows = [[InlineKeyboardButton(k, callback_data=f"wom_{i}")] for i, k in enumerate(keys)]
        kb_rows.append([back_btn("main_menu")])
        await safe_edit(query, "🌸 *أحكام المرأة والأدعية*\nاختر القسم:", reply_markup=InlineKeyboardMarkup(kb_rows))
        return

    # ── Friday: fri_IDX / fri_surahs ─────────────────────────────
    if data.startswith("fri_") and data != "fri_surahs":
        idx  = int(data.split("_")[1])
        if idx >= len(FRIDAY_SUNNAN): return
        s = FRIDAY_SUNNAN[idx]
        kb = InlineKeyboardMarkup([[back_btn("friday_menu")]])
        await safe_edit(query, f"⭐ *{s['title']}*\n\n{s['text']}\n\n📖 _{s['source']}_", reply_markup=kb)
        return

    if data == "fri_surahs":
        lines = "\n\n".join([f"📖 سورة {SURAH_NAMES[num]}\n{desc}" for num, desc in FRIDAY_SURAHS.items()])
        kb = InlineKeyboardMarkup([[back_btn("friday_menu")]])
        await safe_edit(query, f"📖 *سور يوم الجمعة*\n\n{lines}", reply_markup=kb)
        return

    if data == "friday_menu":
        kb_rows = [[InlineKeyboardButton(s["title"], callback_data=f"fri_{i}")] for i, s in enumerate(FRIDAY_SUNNAN)]
        kb_rows.append([InlineKeyboardButton("📖 سور الجمعة", callback_data="fri_surahs")])
        kb_rows.append([back_btn("main_menu")])
        await safe_edit(query, "⭐ *سنن يوم الجمعة*\nاختر:", reply_markup=InlineKeyboardMarkup(kb_rows))
        return

    # ── Change city ───────────────────────────────────────────────
    if data == "change_city":
        context.user_data["state"] = "await_city"
        cities_text = "\n".join(ALGERIAN_CITIES)
        await safe_edit(query, f"🏙️ أرسل اسم مدينتك من القائمة:\n\n{cities_text}")
        return

    # ── Custom buttons: custbtn_ID ────────────────────────────────
    if data.startswith("custbtn_"):
        btn_id = int(data.split("_")[1])
        btn    = get_button_by_id(btn_id)
        if btn:
            kb = InlineKeyboardMarkup([[back_btn("main_menu")]])
            await safe_edit(query, btn[3], reply_markup=kb)
        else:
            await query.answer("⚠️ الزر غير موجود.")
        return

    # ══════════════════════════════════════════════════════════════
    # ADMIN CALLBACKS
    # ══════════════════════════════════════════════════════════════
    if not is_admin(uid):
        await query.answer("⛔ ليس لديك صلاحية.")
        return

    if data == "adm_panel":
        stats = get_admin_stats()
        msg = (
            f"⚙️ *لوحة الإدارة*\n\n"
            f"👥 المستخدمون: {stats['users']}\n"
            f"🛡 المشرفون: {stats['admins']}\n"
            f"🚫 المحظورون: {stats['banned']}\n"
            f"✅ نشطون اليوم: {stats['active_today']}\n"
            f"📚 الأحاديث: {stats['hadiths']}\n"
            f"🤲 الأدعية: {stats['duas']}\n"
            f"📝 المحتوى: {stats['content']}\n"
            f"📿 مجموع التسبيح: {stats['tasbih_total']}\n"
            f"📋 معلق: {stats['pending']} | ✅ مُجاب: {stats['replied']}"
        )
        await safe_edit(query, msg, reply_markup=build_admin_keyboard())
        return

    if data == "adm_stats":
        stats = get_admin_stats()
        msg = (
            f"📊 *إحصائيات البوت*\n\n"
            f"👥 إجمالي المستخدمين: {stats['users']}\n"
            f"🛡 المشرفون: {stats['admins']}\n"
            f"🚫 المحظورون: {stats['banned']}\n"
            f"✅ نشطون اليوم: {stats['active_today']}\n"
            f"📚 الأحاديث: {stats['hadiths']}\n"
            f"🤲 الأدعية: {stats['duas']}\n"
            f"📝 المحتوى المخصص: {stats['content']}\n"
            f"📿 مجموع التسبيح الكلي: {stats['tasbih_total']}\n"
            f"📋 استفسارات معلقة: {stats['pending']}\n"
            f"✅ استفسارات مُجابة: {stats['replied']}"
        )
        await safe_edit(query, msg, reply_markup=InlineKeyboardMarkup([[back_btn("adm_panel")]]))
        return

    if data == "adm_inquiries":
        rows = get_pending_inquiries()
        if not rows:
            await safe_edit(query, "✅ لا توجد استفسارات معلقة.", reply_markup=InlineKeyboardMarkup([[back_btn("adm_panel")]]))
            return
        lines = "\n\n".join([f"#{r[0]} — {r[3]} (@{r[2] or '—'}) | {r[5][:10]}\n{r[4][:100]}" for r in rows])
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ رد على استفسار", callback_data="adm_do_reply")],
            [back_btn("adm_panel")],
        ])
        await safe_edit(query, f"📋 *الاستفسارات المعلقة:*\n\n{lines}", reply_markup=kb)
        return

    if data == "adm_all_inquiries":
        rows = get_all_inquiries(20)
        if not rows:
            await safe_edit(query, "لا توجد استفسارات.", reply_markup=InlineKeyboardMarkup([[back_btn("adm_panel")]]))
            return
        lines = "\n\n".join([f"#{r[0]} [{r[5]}] — {r[3]}\n{r[4][:80]}" for r in rows])
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ رد على استفسار", callback_data="adm_do_reply")],
            [back_btn("adm_panel")],
        ])
        await safe_edit(query, f"📜 *كل الاستفسارات:*\n\n{lines}", reply_markup=kb)
        return

    if data == "adm_do_reply":
        context.user_data["state"] = "await_reply_id"
        await safe_edit(query, "✏️ أرسل رقم الاستفسار للرد عليه:")
        return

    if data == "adm_add_hadith":
        context.user_data["state"] = "await_hadith"
        await safe_edit(query, "✏️ أرسل الحديث بالصيغة:\n\nنص الحديث | المصدر")
        return

    if data == "adm_del_hadith":
        con  = sqlite3.connect(DB_PATH)
        rows = con.execute("SELECT id, text FROM hadiths ORDER BY id DESC LIMIT 10").fetchall()
        con.close()
        if not rows:
            await safe_edit(query, "⚠️ لا توجد أحاديث.", reply_markup=InlineKeyboardMarkup([[back_btn("adm_panel")]]))
            return
        lines = "\n".join([f"#{r[0]}: {r[1][:60]}..." for r in rows])
        context.user_data["state"] = "await_del_hadith_id"
        await safe_edit(query, f"🗑 الأحاديث الأخيرة:\n\n{lines}\n\nأرسل رقم الحديث لحذفه:")
        return

    if data == "adm_add_dua":
        context.user_data["state"] = "await_dua"
        await safe_edit(query, "✏️ أرسل الدعاء بالصيغة:\n\nنص الدعاء | المصدر")
        return

    if data == "adm_del_dua":
        con  = sqlite3.connect(DB_PATH)
        rows = con.execute("SELECT id, text FROM duas ORDER BY id DESC LIMIT 10").fetchall()
        con.close()
        if not rows:
            await safe_edit(query, "⚠️ لا توجد أدعية.", reply_markup=InlineKeyboardMarkup([[back_btn("adm_panel")]]))
            return
        lines = "\n".join([f"#{r[0]}: {r[1][:60]}..." for r in rows])
        context.user_data["state"] = "await_del_dua_id"
        await safe_edit(query, f"🗑 الأدعية الأخيرة:\n\n{lines}\n\nأرسل رقم الدعاء لحذفه:")
        return

    if data == "adm_add_content":
        context.user_data["state"] = "await_content"
        await safe_edit(query, "✏️ أرسل المحتوى بالصيغة:\n\nالفئة | النص | المصدر")
        return

    if data == "adm_del_content":
        con  = sqlite3.connect(DB_PATH)
        rows = con.execute("SELECT id, category, text FROM bot_content ORDER BY id DESC LIMIT 10").fetchall()
        con.close()
        if not rows:
            await safe_edit(query, "⚠️ لا يوجد محتوى.", reply_markup=InlineKeyboardMarkup([[back_btn("adm_panel")]]))
            return
        lines = "\n".join([f"#{r[0]} [{r[1]}]: {r[2][:50]}..." for r in rows])
        context.user_data["state"] = "await_del_content_id"
        await safe_edit(query, f"🗑 المحتوى الأخير:\n\n{lines}\n\nأرسل رقم المحتوى لحذفه:")
        return

    if data == "adm_add_admin":
        context.user_data["state"] = "await_add_admin"
        await safe_edit(query, "✏️ أرسل معرف (ID) المستخدم الذي تريد تعيينه مشرفاً:")
        return

    if data == "adm_del_admin":
        admins = get_all_admins()
        lines  = "\n".join([str(a) for a in admins if a not in SUPER_ADMINS])
        context.user_data["state"] = "await_del_admin"
        await safe_edit(query, f"المشرفون الحاليون:\n{lines or 'لا يوجد'}\n\nأرسل ID المشرف لإزالته:")
        return

    if data == "adm_ban":
        context.user_data["state"] = "await_ban"
        await safe_edit(query, "🚫 أرسل معرف (ID) المستخدم لحظره:")
        return

    if data == "adm_unban":
        context.user_data["state"] = "await_unban"
        await safe_edit(query, "✅ أرسل معرف (ID) المستخدم لرفع الحظر عنه:")
        return

    if data == "adm_broadcast":
        context.user_data["state"] = "await_broadcast"
        await safe_edit(query, "📢 أرسل الرسالة التي تريد بثها لجميع المستخدمين:")
        return

    if data == "adm_send_user":
        context.user_data["state"] = "await_send_user_id"
        await safe_edit(query, "📩 أرسل معرف (ID) المستخدم:")
        return

    if data == "adm_users_list":
        rows  = get_users_list(30)
        lines = "\n".join([f"{'🛡' if r[3] else '🚫' if r[4] else '👤'} {r[2] or '—'} | `{r[0]}` | {r[5][:10]}" for r in rows])
        await safe_edit(query, f"👥 *قائمة المستخدمين (آخر 30):*\n\n{lines}", reply_markup=InlineKeyboardMarkup([[back_btn("adm_panel")]]))
        return

    if data == "adm_custom_btns":
        btns  = get_all_custom_buttons()
        lines = "\n".join([f"#{b[0]} [{b[1]}] {b[2]}" for b in btns]) if btns else "لا توجد أزرار مخصصة."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ إضافة زر مخصص",  callback_data="adm_add_custbtn")],
            [InlineKeyboardButton("🗑 حذف زر مخصص",    callback_data="adm_del_custbtn")],
            [back_btn("adm_panel")],
        ])
        await safe_edit(query, f"🔘 *الأزرار المخصصة:*\n\n{lines}", reply_markup=kb)
        return

    if data == "adm_add_custbtn":
        sections = "\n".join(SECTIONS.keys())
        context.user_data["state"] = "await_custom_btn"
        await safe_edit(query, f"✏️ أرسل بالصيغة:\nاسم_القسم | اسم الزر | المحتوى\n\nالأقسام المتاحة:\n{sections}")
        return

    if data == "adm_del_custbtn":
        btns = get_all_custom_buttons()
        if not btns:
            await safe_edit(query, "⚠️ لا توجد أزرار.", reply_markup=InlineKeyboardMarkup([[back_btn("adm_panel")]]))
            return
        kb_rows = [[InlineKeyboardButton(f"🗑 #{b[0]} {b[2]}", callback_data=f"adm_delbtn_{b[0]}")] for b in btns]
        kb_rows.append([back_btn("adm_custom_btns")])
        await safe_edit(query, "اختر الزر لحذفه:", reply_markup=InlineKeyboardMarkup(kb_rows))
        return

    if data.startswith("adm_delbtn_"):
        btn_id = int(data.split("_")[2])
        delete_custom_button(btn_id)
        await safe_edit(query, f"✅ تم حذف الزر #{btn_id}.", reply_markup=InlineKeyboardMarkup([[back_btn("adm_custom_btns")]]))
        return

    # Fallback
    await query.answer("⚠️ غير معروف.")

# ══════════════════════════════════════════════════════════════════
# SCHEDULED JOBS
# ══════════════════════════════════════════════════════════════════
async def job_morning(context: ContextTypes.DEFAULT_TYPE):
    msg = "🌅 *صباح الخير!*\nلا تنس أذكار الصباح 🌿\nاضغط /start للبدء."
    for uid in get_all_users():
        if not notif_already_sent(uid, "morning"):
            try:
                await context.bot.send_message(uid, msg, parse_mode=ParseMode.MARKDOWN)
                mark_notif_sent(uid, "morning")
            except Exception:
                pass

async def job_evening(context: ContextTypes.DEFAULT_TYPE):
    msg = "🌆 *مساء الخير!*\nلا تنس أذكار المساء 🌿\nاضغط /start للبدء."
    for uid in get_all_users():
        if not notif_already_sent(uid, "evening"):
            try:
                await context.bot.send_message(uid, msg, parse_mode=ParseMode.MARKDOWN)
                mark_notif_sent(uid, "evening")
            except Exception:
                pass

async def job_friday(context: ContextTypes.DEFAULT_TYPE):
    if datetime.now().weekday() != 4: return  # Friday only
    msg = "⭐ *يوم الجمعة المبارك!*\nلا تنس قراءة سورة الكهف والإكثار من الصلاة على النبي ﷺ\nاضغط /start للمزيد."
    for uid in get_all_users():
        if not notif_already_sent(uid, "friday"):
            try:
                await context.bot.send_message(uid, msg, parse_mode=ParseMode.MARKDOWN)
                mark_notif_sent(uid, "friday")
            except Exception:
                pass

# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════
def main():
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    jq = app.job_queue
    if jq is not None:
        jq.run_daily(job_morning, time=time(5, 30, tzinfo=timezone.utc))
        jq.run_daily(job_evening, time=time(16, 0, tzinfo=timezone.utc))
        jq.run_daily(job_friday,  time=time(6,  0, tzinfo=timezone.utc))
        logger.info("✅ JobQueue مفعّل — التنبيهات اليومية جاهزة.")
    else:
        logger.warning("⚠️ JobQueue غير مثبّت — التنبيهات اليومية معطّلة. لتفعيلها: pip install 'python-telegram-bot[job-queue]'")

    logger.info("🤖 البوت يعمل...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
