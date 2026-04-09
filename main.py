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
    91:15,92:21,93:11,94:8,95:8,96:19,97:5,98:,99:8,100:11,
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
    ("سُبْحَانَ اللَّهِ",                                          "تمحو الخطايا — رواه مسلم",              33),
    ("الْحَمْدُ لِلَّهِ",                                          "تملأ الميزان — رواه مسلم",               33),
    ("اللَّهُ أَكْبَرُ",                                           "تملأ ما بين السماء والأرض",               33),
    ("لَا إِلَهَ إِلَّا اللَّهُ",                                  "أفضل الذكر — رواه الترمذي",              100),
    ("لَا حَوْلَ وَلَا قُوَّةَ إِلَّا بِاللَّهِ",                "كنز من كنوز الجنة — متفق عليه",          100),
    ("سُبْحَانَ اللَّهِ وَبِحَمْدِهِ سُبْحَانَ اللَّهِ الْعَظِيمِ","أحب الكلام إلى الله — متفق عليه",       100),
    ("أَسْتَغْفِرُ اللَّهَ",                                       "من لزمه فتح الله له كل مضيق — أبو داود", 100),
    ("اللَّهُمَّ صَلِّ وَسَلِّمْ عَلَى نَبِيِّنَا مُحَمَّدٍ",   "من صلى عليه مرة صلى الله عليه عشرا",    100),
    ("سُبْحَانَ اللَّهِ وَبِحَمْدِهِ",                            "من قالها مئة غُفرت خطاياه — البخاري",    100),
    ("اللَّهُمَّ اغْفِرْ لِي وَتُبْ عَلَيَّ",                    "رواه أبو داود صحيح",                      100),
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
# قاعدة البيانات
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
            section TEXT NOT NULL,
            btn_label TEXT NOT NULL,
            btn_content TEXT NOT NULL,
            added_by INTEGER,
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
    return (row[0], row[1]) if row else (2, 0)

def save_surah_progress(uid, surah, ayah, riwaya="hafs"):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO surah_progress (user_id, surah, riwaya, last_ayah) VALUES (?,?,?,?) ON CONFLICT(user_id, surah, riwaya) DO UPDATE SET last_ayah=excluded.last_ayah", (uid, surah, riwaya, ayah))
    con.commit(); con.close()

def get_surah_progress(uid, surah, riwaya="hafs"):
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT last_ayah FROM surah_progress WHERE user_id=? AND surah=? AND riwaya=?", (uid, surah, riwaya)).fetchone()
    con.close()
    return row[0] if row else 0

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

# ── Custom Buttons DB ──────────────────────────────────────────────
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
# API Helpers
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
# أدوات مساعدة
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
    except:
        await query.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)

def back_btn(target="main_menu"):
    return InlineKeyboardButton("🔙 رجوع", callback_data=target)

# ══════════════════════════════════════════════════════════════════
# لوحات المفاتيح
# ══════════════════════════════════════════════════════════════════
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
    per   = 20
    start = page * per
    end   = min(start + per, 114)
    rows  = []
    chunk = surahs[start:end]
    for i in range(0, len(chunk), 4):
        row = [InlineKeyboardButton(f"{num}. {name}", callback_data=f"ss_{num}_{riwaya}") for num, name in chunk[i:i+4]]
        rows.append(row)
    nav = []
    if page > 0:  nav.append(InlineKeyboardButton("◀️ السابق", callback_data=f"sp_{page-1}_{riwaya}"))
    if end < 114: nav.append(InlineKeyboardButton("التالي ▶️", callback_data=f"sp_{page+1}_{riwaya}"))
    if nav: rows.append(nav)
    rows.append([back_btn("quran_menu")])
    return InlineKeyboardMarkup(rows)

def build_section_keyboard(section_key, back_target="main_menu"):
    """Build keyboard for any section, appending custom buttons from DB."""
    custom = get_custom_buttons(section_key)
    rows = []
    for btn_id, label, _ in custom:
        rows.append([InlineKeyboardButton(label, callback_data=f"custbtn_{btn_id}")])
    rows.append([back_btn(back_target)])
    return InlineKeyboardMarkup(rows)

# ══════════════════════════════════════════════════════════════════
# SECTIONS MAP — used for admin to pick where to add a button
# ══════════════════════════════════════════════════════════════════
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
# HANDLERS — Start / Main Menu
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
# MESSAGE HANDLER — routes text messages
# ══════════════════════════════════════════════════════════════════
@banned_check
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u    = update.effective_user
    text = update.message.text.strip()
    upsert_user(u.id, u.username, u.first_name, u.last_name)
    state = context.user_data.get("state")

    # ── Awaiting states ────────────────────────────────────────────
    if state == "awaiting_inquiry":
        # User typed their inquiry message
        msg = text
        iid = save_inquiry(u.id, u.username, u.first_name, msg)
        log_activity(u.id, "inquiry", msg[:50])
        context.user_data.clear()
        # Notify admins
        admins = get_all_admins()
        notif  = (
            f"📩 *استفسار جديد #{iid}*\n"
            f"👤 {u.first_name} (@{u.username or '—'})\n"
            f"🆔 `{u.id}`\n\n"
            f"💬 {msg}\n\n"
            f"للرد: اضغط على الزر أدناه"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"↩️ رد على #{iid}", callback_data=f"adm_reply_{iid}")]])
        for adm in admins:
            try:
                await context.bot.send_message(adm, notif, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
            except: pass
        await update.message.reply_text(
            "✅ تم إرسال استفسارك بنجاح! سيرد عليك المشرف قريباً إن شاء الله.",
            reply_markup=get_main_keyboard(u.id)
        )
        return

    if state == "awaiting_admin_reply":
        iid       = context.user_data.get("reply_iid")
        target_uid = context.user_data.get("reply_uid")
        context.user_data.clear()
        if not iid or not target_uid:
            await update.message.reply_text("⚠️ انتهت الجلسة.", reply_markup=get_main_keyboard(u.id))
            return
        reply_to_inquiry(iid, text)
        try:
            await context.bot.send_message(target_uid, f"📬 *رد على استفسارك #{iid}:*\n\n{text}", parse_mode=ParseMode.MARKDOWN)
            await update.message.reply_text("✅ تم إرسال الرد للمستخدم.", reply_markup=get_main_keyboard(u.id))
        except:
            await update.message.reply_text("⚠️ تعذّر إيصال الرد للمستخدم.", reply_markup=get_main_keyboard(u.id))
        return

    if state == "awaiting_add_hadith":
        parts = text.split("|", 1)
        if len(parts) < 2:
            await update.message.reply_text("⚠️ الصيغة: نص الحديث | المصدر\nحاول مرة أخرى أو /start للإلغاء.")
            return
        con = sqlite3.connect(DB_PATH)
        con.execute("INSERT INTO hadiths (text, source, added_by) VALUES (?,?,?)", (parts[0].strip(), parts[1].strip(), u.id))
        con.commit(); con.close()
        context.user_data.clear()
        await update.message.reply_text("✅ تمت إضافة الحديث.", reply_markup=get_main_keyboard(u.id))
        return

    if state == "awaiting_add_dua":
        parts = text.split("|", 1)
        if len(parts) < 2:
            await update.message.reply_text("⚠️ الصيغة: نص الدعاء | المصدر\nحاول مرة أخرى أو /start للإلغاء.")
            return
        con = sqlite3.connect(DB_PATH)
        con.execute("INSERT INTO duas (text, source, added_by) VALUES (?,?,?)", (parts[0].strip(), parts[1].strip(), u.id))
        con.commit(); con.close()
        context.user_data.clear()
        await update.message.reply_text("✅ تمت إضافة الدعاء.", reply_markup=get_main_keyboard(u.id))
        return

    if state == "awaiting_add_content":
        parts = text.split("|", 2)
        if len(parts) < 3:
            await update.message.reply_text("⚠️ الصيغة: التصنيف | النص | المصدر\nحاول مرة أخرى.")
            return
        con = sqlite3.connect(DB_PATH)
        con.execute("INSERT INTO bot_content (category, text, source, added_by) VALUES (?,?,?,?)", (parts[0].strip(), parts[1].strip(), parts[2].strip(), u.id))
        con.commit(); con.close()
        context.user_data.clear()
        await update.message.reply_text("✅ تمت إضافة المحتوى.", reply_markup=get_main_keyboard(u.id))
        return

    if state == "awaiting_add_admin":
        try:
            new_id = int(text.strip())
            con = sqlite3.connect(DB_PATH)
            con.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?,?,?)", (new_id, "", "مشرف"))
            con.execute("UPDATE users SET is_admin=1 WHERE user_id=?", (new_id,))
            con.commit(); con.close()
            context.user_data.clear()
            await update.message.reply_text(f"✅ تمت إضافة المشرف {new_id}.", reply_markup=get_main_keyboard(u.id))
        except:
            await update.message.reply_text("⚠️ أدخل معرّف رقمي صحيح.")
        return

    if state == "awaiting_del_admin":
        try:
            del_id = int(text.strip())
            if del_id in SUPER_ADMINS:
                await update.message.reply_text("⚠️ لا يمكن حذف المشرف الرئيسي.")
                return
            delete_admin(del_id)
            context.user_data.clear()
            await update.message.reply_text(f"✅ تمت إزالة صلاحيات المشرف {del_id}.", reply_markup=get_main_keyboard(u.id))
        except:
            await update.message.reply_text("⚠️ أدخل معرّف رقمي صحيح.")
        return

    if state == "awaiting_ban":
        try:
            ban_id = int(text.strip())
            ban_user(ban_id)
            context.user_data.clear()
            await update.message.reply_text(f"🚫 تم حظر المستخدم {ban_id}.", reply_markup=get_main_keyboard(u.id))
        except:
            await update.message.reply_text("⚠️ أدخل معرّف رقمي صحيح.")
        return

    if state == "awaiting_unban":
        try:
            unban_id = int(text.strip())
            unban_user(unban_id)
            context.user_data.clear()
            await update.message.reply_text(f"✅ تم رفع الحظر عن {unban_id}.", reply_markup=get_main_keyboard(u.id))
        except:
            await update.message.reply_text("⚠️ أدخل معرّف رقمي صحيح.")
        return

    if state == "awaiting_send_user":
        parts = text.split("|", 1)
        if len(parts) < 2:
            await update.message.reply_text("⚠️ الصيغة: معرف_المستخدم | الرسالة\nحاول مرة أخرى.")
            return
        try:
            target_id  = int(parts[0].strip())
            msg_to_send = parts[1].strip()
            await context.bot.send_message(target_id, msg_to_send)
            context.user_data.clear()
            await update.message.reply_text("✅ تم الإرسال.", reply_markup=get_main_keyboard(u.id))
        except:
            await update.message.reply_text("⚠️ تعذّر الإرسال.", reply_markup=get_main_keyboard(u.id))
        return

    if state == "awaiting_broadcast":
        all_users = get_all_users()
        sent = 0
        for uid_ in all_users:
            try:
                await context.bot.send_message(uid_, text)
                sent += 1
            except: pass
        context.user_data.clear()
        await update.message.reply_text(f"📢 تم الإرسال لـ {sent} مستخدم.", reply_markup=get_main_keyboard(u.id))
        return

    if state == "awaiting_custom_btn_label":
        context.user_data["new_btn_label"] = text
        context.user_data["state"] = "awaiting_custom_btn_content"
        await update.message.reply_text(
            "📝 أرسل الآن *محتوى* الزر (النص الذي سيظهر عند الضغط عليه):",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if state == "awaiting_custom_btn_content":
        section = context.user_data.get("new_btn_section")
        label   = context.user_data.get("new_btn_label")
        content = text
        context.user_data.clear()
        if not section or not label:
            await update.message.reply_text("⚠️ حدث خطأ، حاول مجدداً.", reply_markup=get_main_keyboard(u.id))
            return
        add_custom_button(section, label, content, u.id)
        await update.message.reply_text(
            f"✅ تمت إضافة الزر *{label}* في قسم *{SECTIONS.get(section, section)}* بنجاح!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard(u.id)
        )
        return

    if state == "awaiting_city":
        city_input = text.strip()
        matched = next((c for c in ALGERIAN_CITIES if c.lower() == city_input.lower()), None)
        if not matched:
            matched = next((c for c in ALGERIAN_CITIES if city_input.lower() in c.lower()), None)
        if matched:
            save_user_city(u.id, matched)
            context.user_data.clear()
            result = await fetch_prayer_times(matched)
            await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(u.id))
        else:
            await update.message.reply_text("⚠️ ل اسماً صحيحاً من القائمة.", reply_markup=get_main_keyboard(u.id))
        return

    # ── Main menu routing ──────────────────────────────────────────
    if text == "📖 القرآن الكريم":
        log_activity(u.id, "quran_menu")
        await update.message.reply_text("📖 *القرآن الكريم*\nاختر رواية:", parse_mode=ParseMode.MARKDOWN, reply_markup=build_quran_keyboard())
    elif text == "🌿 الورد اليومي":
        log_activity(u.id, "wird")
        await show_wird(update, context)
    elif text == "📿 التسبيح":
        log_activity(u.id, "tasbih")
        await show_tasbih(update, context)
    elif text == "🌅 أذكار الصباح":
        log_activity(u.id, "morning_adhkar")
        await show_adhkar_menu(update, context, "morning_adhkar", "🌅 أذكار الصباح", MORNING_ADHKAR)
    elif text == "🌆 أذكار المساء":
        log_activity(u.id, "evening_adhkar")
        await show_adhkar_menu(update, context, "evening_adhkar", "🌆 أذكار المساء", EVENING_ADHKAR)
    elif text == "🌙 أذكار النوم":
        log_activity(u.id, "sleep_adhkar")
        await show_adhkar_menu(update, context, "sleep_adhkar", "🌙 أذكار النوم", SLEEP_ADHKAR)
    elif text == "🌺 أذكار الاستيقاظ":
        log_activity(u.id, "wakeup_adhkar")
        await show_adhkar_menu(update, context, "wakeup_adhkar", "🌺 أذكار الاستيقاظ", WAKEUP_ADHKAR)
    elif text == "💧 أذكار الوضوء":
        log_activity(u.id, "wudu_adhkar")
        await show_adhkar_menu(update, context, "wudu_adhkar", "💧 أذكار الوضوء", WUDU_ADHKAR)
    elif text == "🕌 أذكار الصلاة":
        log_activity(u.id, "prayer_adhkar")
        await show_prayer_adhkar_menu(update, context)
    elif text == "🌺 أدعية خاصة":
        log_activity(u.id, "special_duas")
        await show_special_duas_menu(update, context)
    elif text == "🌸 أحكام المرأة":
        log_activity(u.id, "woman_adhkar")
        await show_woman_adhkar_menu(update, context)
    elif text == "⭐ سنن يوم الجمعة":
        log_activity(u.id, "friday")
        await show_friday_menu(update, context)
    elif text == "🕐 أوقات الصلاة":
        log_activity(u.id, "prayer_times")
        await show_prayer_times(update, context)
    elif text == "📅 التاريخ اليوم":
        log_activity(u.id, "date")
        result = await fetch_dates()
        await update.message.reply_text(result, reply_markup=get_main_keyboard(u.id))
    elif text == "📚 حديث اليوم":
        log_activity(u.id, "hadith")
        row = get_random_hadith()
        if row:
            await update.message.reply_text(f"📚 *حديث اليوم*\n\n{row[0]}\n\n📖 _{row[1]}_", parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(u.id))
        else:
            await update.message.reply_text("لا توجد أحاديث بعد. يمكن للمشرف إضافة أحاديث من لوحة الإدارة.", reply_markup=get_main_keyboard(u.id))
    elif text == "🤲 دعاء اليوم":
        log_activity(u.id, "dua")
        row = get_random_dua()
        if row:
            await update.message.reply_text(f"🤲 *دعاء اليوم*\n\n{row[0]}\n\n📖 _{row[1]}_", parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(u.id))
        else:
            await update.message.reply_text("لا توجد أدعية بعد. يمكن للمشرف إضافة أدعية من لوحة الإدارة.", reply_markup=get_main_keyboard(u.id))
    elif text == "🎓 الدورات المجانية":
        log_activity(u.id, "courses")
        await show_courses(update, context)
    elif text == "📊 إحصائياتي":
        log_activity(u.id, "stats")
        await show_user_stats(update, context)
    elif text == "💬 استفسار":
        log_activity(u.id, "inquiry_start")
        await start_inquiry(update, context)
    elif text == "ℹ️ المساعدة":
        await cmd_help(update, context)
    elif text == "⚙️ لوحة الإدارة":
        if not is_admin(u.id):
            await update.message.reply_text("⛔ ليس لديك صلاحية.")
            return
        log_activity(u.id, "admin_panel")
        await update.message.reply_text("⚙️ *لوحة الإدارة*", parse_mode=ParseMode.MARKDOWN, reply_markup=build_admin_keyboard())
    else:
        await update.message.reply_text("اختر من القائمة 👇", reply_markup=get_main_keyboard(u.id))

# ══════════════════════════════════════════════════════════════════
# INQUIRY
# ══════════════════════════════════════════════════════════════════
async def start_inquiry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_inquiry")]])
    context.user_data["state"] = "awaiting_inquiry"
    await update.message.reply_text(
        "💬 *استفسار*\n\nاكتب استفسارك وسيصل للمشرفين مباشرة.\nأو اضغط إلغاء للرجوع.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )

# ══════════════════════════════════════════════════════════════════
# WIRD
# ══════════════════════════════════════════════════════════════════
async def show_wird(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    surah, ayah = get_wird_progress(u.id)
    total = SURAH_AYAH_COUNT.get(surah, 1)
    pct   = int((ayah / total) * 100) if total else 0
    bar   = "█" * (pct // 10) + "░" * (10 - pct // 10)
    text  = (
        f"🌿 *الورد اليومي*\n\n"
        f"📖 سورة: *{SURAH_NAMES.get(surah, surah)}* ({surah})\n"
        f"📍 الآية: *{ayah}* / {total}\n"
        f"📊 `{bar}` {pct}%"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ متابعة القراءة", callback_data=f"wird_read_{surah}_{ayah}")],
        [InlineKeyboardButton("🔄 إعادة الضبط",    callback_data="wird_reset")],
        [back_btn("main_menu")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

# ══════════════════════════════════════════════════════════════════
# TASBIH
# ══════════════════════════════════════════════════════════════════
async def show_tasbih(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    idx, cnt = get_tasbih_session(u.id)
    if idx >= len(TASBIH_LIST): idx = 0
    phrase, fadl, target = TASBIH_LIST[idx]
    text = (
        f"📿 *التسبيح* ({idx+1}/{len(TASBIH_LIST)})\n\n"
        f"*{phrase}*\n\n"
        f"💡 _{fadl}_\n\n"
        f"العدد: *{cnt}* / {target}"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ تسبيحة", callback_data="tsb_inc"),
         InlineKeyboardButton("🔄 تصفير",  callback_data="tsb_reset")],
        [InlineKeyboardButton("⏭ التالي",  callback_data="tsb_next"),
         InlineKeyboardButton("⏮ السابق", callback_data="tsb_prev")],
        [InlineKeyboardButton("📊 إحصائياتي", callback_data="tsb_stats")],
        [back_btn("main_menu")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

# ══════════════════════════════════════════════════════════════════
# ADHKAR helpers
# ══════════════════════════════════════════════════════════════════
async def show_adhkar_menu(update, context, key, title, adhkar_list):
    u   = update.effective_user
    idx = get_adhkar_progress(u.id, key)
    total = len(adhkar_list)
    if idx >= total:
        custom_btns = get_custom_buttons(key)
        rows = [[InlineKeyboardButton(lb, callback_data=f"custbtn_{bid}")] for bid, lb, _ in custom_btns]
        rows.append([InlineKeyboardButton("🔄 إعادة من البداية", callback_data=f"adhkar_restart_{key}")])
        rows.append([back_btn("main_menu")])
        msg = await (update.message or update.callback_query.message)
        if hasattr(update, "message") and update.message:
            await update.message.reply_text(f"✅ *{title}*\n\nأتممت جميع الأذكار بارك الله فيك! 🌟", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(rows))
        else:
            await update.callback_query.message.edit_text(f"✅ *{title}*\n\nأتممت جميع الأذكار بارك الله فيك! 🌟", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(rows))
        return
    dhikr, source, target = adhkar_list[idx]
    text = (
        f"*{title}*\n\n"
        f"📿 *{idx+1}/{total}*\n\n"
        f"{dhikr}\n\n"
        f"📖 _{source}_\n"
        f"🔢 العدد المطلوب: *{target}*"
    )
    custom_btns = get_custom_buttons(key)
    extra_rows  = [[InlineKeyboardButton(lb, callback_data=f"custbtn_{bid}")] for bid, lb, _ in custom_btns]
    kb_rows = [
        [InlineKeyboardButton("✅ تم", callback_data=f"adhkar_done_{key}_{idx}"),
         InlineKeyboardButton("⏭ التالي", callback_data=f"adhkar_next_{key}_{idx}")],
        [InlineKeyboardButton("⏮ السابق", callback_data=f"adhkar_prev_{key}_{idx}"),
         InlineKeyboardButton("🔄 إعادة", callback_data=f"adhkar_restart_{key}")],
    ] + extra_rows + [[back_btn("main_menu")]]
    if hasattr(update, "message") and update.message:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb_rows))
    else:
        await update.callback_query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb_rows))

async def show_prayer_adhkar_menu(update, context):
    u = update.effective_user
    keys = list(PRAYER_ADHKAR.keys())
    custom_btns = get_custom_buttons("prayer_adhkar")
    rows = [[InlineKeyboardButton(k, callback_data=f"padh_{i}")] for i, k in enumerate(keys)]
    for bid, lb, _ in custom_btns:
        rows.append([InlineKeyboardButton(lb, callback_data=f"custbtn_{bid}")])
    rows.append([back_btn("main_menu")])
    await update.message.reply_text("🕌 *أذكار الصلاة*\nاختر القسم:", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(rows))

async def show_special_duas_menu(update, context):
    keys = list(SPECIAL_DUAS.keys())
    custom_btns = get_custom_buttons("special_duas")
    rows = [[InlineKeyboardButton(k, callback_data=f"sdua_{i}")] for i, k in enumerate(keys)]
    for bid, lb, _ in custom_btns:
        rows.append([InlineKeyboardButton(lb, callback_data=f"custbtn_{bid}")])
    rows.append([back_btn("main_menu")])
    await update.message.reply_text("🌺 *أدعية خاصة*\nاختر الدعاء:", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(rows))

async def show_woman_adhkar_menu(update, context):
    keys = list(WOMAN_ADHKAR.keys())
    custom_btns = get_custom_buttons("woman_adhkar")
    rows = [[InlineKeyboardButton(k, callback_data=f"wadh_{i}")] for i, k in enumerate(keys)]
    for bid, lb, _ in custom_btns:
        rows.append([InlineKeyboardButton(lb, callback_data=f"custbtn_{bid}")])
    rows.append([back_btn("main_menu")])
    await update.message.reply_text("🌸 *أحكام المرأة*\nاختر القسم:", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(rows))

async def show_friday_menu(update, context):
    custom_btns = get_custom_buttons("friday_sunnan")
    rows = [[InlineKeyboardButton(s["title"], callback_data=f"fri_{i}")] for i, s in enumerate(FRIDAY_SUNNAN)]
    rows.append([InlineKeyboardButton("📖 سور الجمعة", callback_data="fri_surahs")])
    for bid, lb, _ in custom_btns:
        rows.append([InlineKeyboardButton(lb, callback_data=f"custbtn_{bid}")])
    rows.append([back_btn("main_menu")])
    await update.message.reply_text("⭐ *سنن يوم الجمعة*", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(rows))

async def show_prayer_times(update, context):
    u    = update.effective_user
    city = get_user_city(u.id)
    if city:
        result = await fetch_prayer_times(city)
        await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(u.id))
    else:
        cities_kb = [[city] for city in ALGERIAN_CITIES]
        await update.message.reply_text(
            "🕐 *أوقات الصلاة*\nاختر مدينتك:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ReplyKeyboardMarkup(cities_kb + [["🔙 رجوع"]], resize_keyboard=True, one_time_keyboard=True)
        )
        context.user_data["state"] = "awaiting_city"

async def show_courses(update, context):
    u = update.effective_user
    custom_btns = get_custom_buttons("courses")
    rows = []
    for bid, lb, _ in custom_btns:
        rows.append([InlineKeyboardButton(lb, callback_data=f"custbtn_{bid}")])
    rows.append([back_btn("main_menu")])
    text = (
        "🎓 *الدورات المجانية*\n\n"
        "• منصة إسلام هاوس: islamhouse.com\n"
        "• موقع الإسلام سؤال وجواب: islamqa.info\n"
        "• موقع طريق الإسلام: ar.islamway.net\n\n"
        "يمكن للمشرف إضافة روابط دورات مباشرة هنا."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(rows))

async def show_user_stats(update, context):
    u     = update.effective_user
    stats = get_user_full_stats(u.id)
    sname = SURAH_NAMES.get(stats["wird_surah"], stats["wird_surah"])
    tsb_lines = "\n".join([f"  • {p}: {c}" for p, c in stats["tasbih"]]) if stats["tasbih"] else "  لا توجد بيانات"
    text = (
        f"📊 *إحصائياتك*\n\n"
        f"🌿 الورد: سورة {sname} آية {stats['wird_ayah']}\n"
        f"📖 السور المكتملة: {stats['surahs_done']}\n"
        f"📿 إجمالي التسبيح: {stats['total_t']}\n"
        f"💬 استفساراتك: {stats['inquiries']}\n\n"
        f"🔝 *أكثر التسابيح:*\n{tsb_lines}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(u.id))

# ══════════════════════════════════════════════════════════════════
# CALLBACK QUERY HANDLER
# ══════════════════════════════════════════════════════════════════
@banned_check
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data  = query.data
    u     = query.from_user
    upsert_user(u.id, u.username, u.first_name, u.last_name)

    # ── Cancel inquiry ─────────────────────────────────────────────
    if data == "cancel_inquiry":
        context.user_data.clear()
        await query.message.edit_text(
            "❌ تم إلغاء الاستفسار.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]])
        )
        return

    # ── Main menu ──────────────────────────────────────────────────
    if data == "main_menu":
        context.user_data.clear()
        await query.message.reply_text("القائمة الرئيسية 👇", reply_markup=get_main_keyboard(u.id))
        try: await query.message.delete()
        except: pass
        return

    # ── Quran ──────────────────────────────────────────────────────
    if data == "quran_menu":
        await safe_edit(query, "📖 *القرآن الكريم*\nاختر رواية:", reply_markup=build_quran_keyboard())
        return

    if data == "quran_random":
        s = random.randint(1, 114)
        a = random.randint(1, SURAH_AYAH_COUNT[s])
        riwaya = "hafs"
        text_ayah = await fetch_quran_ayah(s, a, riwaya)
        msg = f"🎲 *آية عشوائية*\n\nسورة {SURAH_NAMES[s]} — آية {a}\n\n{text_ayah}"
        kb  = InlineKeyboardMarkup([[InlineKeyboardButton("🎲 آية أخرى", callback_data="quran_random"), back_btn("quran_menu")]])
        await safe_edit(query, msg, reply_markup=kb)
        return

    if data.startswith("sp_"):
        _, page, riwaya = data.split("_", 2)
        await safe_edit(query, f"📖 اختر السورة — رواية {'حفص' if riwaya=='hafs' else 'ورش'}:", reply_markup=build_surah_keyboard(int(page), riwaya))
        return

    if data.startswith("ss_"):
        _, surah_n, riwaya = data.split("_", 2)
        surah_n = int(surah_n)
        last    = get_surah_progress(u.id, surah_n, riwaya)
        start_a = last if last > 0 else 1
        total_a = SURAH_AYAH_COUNT[surah_n]
        ayah_text = await fetch_quran_ayah(surah_n, start_a, riwaya)
        msg = (
            f"📖 *{SURAH_NAMES[surah_n]}* — آية {start_a}/{total_a}\n"
            f"رواية: {'حفص' if riwaya=='hafs' else 'ورش'}\n\n"
            f"{ayah_text}"
        )
        nav = []
        if start_a > 1:
            nav.append(InlineKeyboardButton("◀️ السابقة", callback_data=f"ay_{surah_n}_{start_a-1}_{riwaya}"))
        if start_a < total_a:
            nav.append(InlineKeyboardButton("التالية ▶️", callback_data=f"ay_{surah_n}_{start_a+1}_{riwaya}"))
        kb = InlineKeyboardMarkup([nav, [back_btn(f"sp_0_{riwaya}")]])
        save_surah_progress(u.id, surah_n, start_a, riwaya)
        await safe_edit(query, msg, reply_markup=kb)
        return

    if data.startswith("ay_"):
        _, sn, an, riwaya = data.split("_", 3)
        sn, an  = int(sn), int(an)
        total_a = SURAH_AYAH_COUNT[sn]
        ayah_text = await fetch_quran_ayah(sn, an, riwaya)
        msg = (
            f"📖 *{SURAH_NAMES[sn]}* — آية {an}/{total_a}\n"
            f"رواية: {'حفص' if riwaya=='hafs' else 'ورش'}\n\n"
            f"{ayah_text}"
        )
        nav = []
        if an > 1:    nav.append(InlineKeyboardButton("◀️ السابقة", callback_data=f"ay_{sn}_{an-1}_{riwaya}"))
        if an < total_a: nav.append(InlineKeyboardButton("التالية ▶️", callback_data=f"ay_{sn}_{an+1}_{riwaya}"))
        kb = InlineKeyboardMarkup([nav, [back_btn(f"sp_0_{riwaya}")]])
        save_surah_progress(u.id, sn, an, riwaya)
        await safe_edit(query, msg, reply_markup=kb)
        return

    # ── Wird ───────────────────────────────────────────────────────
    if data.startswith("wird_read_"):
        _, _, surah_s, ayah_s = data.split("_", 3)
        sn, an = int(surah_s), int(ayah_s)
        if an == 0: an = 1
        total_a   = SURAH_AYAH_COUNT.get(sn, 1)
        ayah_text = await fetch_quran_ayah(sn, an)
        msg = f"🌿 *الورد اليومي*\n\n*{SURAH_NAMES[sn]}* — آية {an}/{total_a}\n\n{ayah_text}"
        nav = []
        if an > 1: nav.append(InlineKeyboardButton("◀️ السابقة", callback_data=f"wird_nav_{sn}_{an-1}"))
        if an < total_a:
            nav.append(InlineKeyboardButton("التالية ▶️", callback_data=f"wird_nav_{sn}_{an+1}"))
        else:
            next_s = sn + 1 if sn < 114 else 2
            nav.append(InlineKeyboardButton(f"▶️ سورة {SURAH_NAMES.get(next_s,'')}", callback_data=f"wird_nav_{next_s}_1"))
        kb = InlineKeyboardMarkup([nav, [back_btn("main_menu")]])
        save_wird_progress(u.id, sn, an)
        await safe_edit(query, msg, reply_markup=kb)
        return

    if data.startswith("wird_nav_"):
        _, _, sn_s, an_s = data.split("_", 3)
        sn, an  = int(sn_s), int(an_s)
        total_a = SURAH_AYAH_COUNT.get(sn, 1)
        ayah_text = await fetch_quran_ayah(sn, an)
        msg = f"🌿 *الورد اليومي*\n\n*{SURAH_NAMES[sn]}* — آية {an}/{total_a}\n\n{ayah_text}"
        nav = []
        if an > 1: nav.append(InlineKeyboardButton("◀️ السابقة", callback_data=f"wird_nav_{sn}_{an-1}"))
        if an < total_a:
            nav.append(InlineKeyboardButton("التالية ▶️", callback_data=f"wird_nav_{sn}_{an+1}"))
        else:
            next_s = sn + 1 if sn < 114 else 2
            nav.append(InlineKeyboardButton(f"▶️ سورة {SURAH_NAMES.get(next_s,'')}", callback_data=f"wird_nav_{next_s}_1"))
        kb = InlineKeyboardMarkup([nav, [back_btn("main_menu")]])
        save_wird_progress(u.id, sn, an)
        await safe_edit(query, msg, reply_markup=kb)
        return

    if data == "wird_reset":
        save_wird_progress(u.id, 2, 0)
        await safe_edit(query, "🔄 تم إعادة ضبط الورد من سورة البقرة.", reply_markup=InlineKeyboardMarkup([[back_btn("main_menu")]]))
        return

    # ── Tasbih ─────────────────────────────────────────────────────
    if data == "tsb_inc":
        idx, cnt = get_tasbih_session(u.id)
        if idx >= len(TASBIH_LIST): idx = 0
        phrase, fadl, target = TASBIH_LIST[idx]
        cnt += 1
        save_tasbih_session(u.id, idx, cnt)
        log_tasbih(u.id, phrase, 1)
        finished = cnt >= target
        if finished:
            msg = f"📿 *{phrase}*\n\n✅ {random.choice(MOTIVATION_MSGS)}\n\nوصلت إلى {target}!"
            kb  = InlineKeyboardMarkup([
                [InlineKeyboardButton("⏭ الذكر التالي", callback_data="tsb_next")],
                [back_btn("main_menu")]
            ])
        else:
            msg = (
                f"📿 *التسبيح* ({idx+1}/{len(TASBIH_LIST)})\n\n"
                f"*{phrase}*\n\n"
                f"💡 _{fadl}_\n\n"
                f"العدد: *{cnt}* / {target}"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ تسبيحة", callback_data="tsb_inc"),
                 InlineKeyboardButton("🔄 تصفير",  callback_data="tsb_reset")],
                [InlineKeyboardButton("⏭ التالي",  callback_data="tsb_next"),
                 InlineKeyboardButton("⏮ السابق", callback_data="tsb_prev")],
                [InlineKeyboardButton("📊 إحصائياتي", callback_data="tsb_stats")],
                [back_btn("main_menu")],
            ])
        await safe_edit(query, msg, reply_markup=kb)
        return

    if data == "tsb_reset":
        idx, _ = get_tasbih_session(u.id)
        save_tasbih_session(u.id, idx, 0)
        phrase, fadl, target = TASBIH_LIST[idx if idx < len(TASBIH_LIST) else 0]
        msg = f"📿 *التسبيح* ({idx+1}/{len(TASBIH_LIST)})\n\n*{phrase}*\n\n💡 _{fadl}_\n\nالعدد: *0* / {target}"
        kb  = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ تسبيحة", callback_data="tsb_inc"),
             InlineKeyboardButton("🔄 تصفير",  callback_data="tsb_reset")],
            [InlineKeyboardButton("⏭ التالي",  callback_data="tsb_next"),
             InlineKeyboardButton("⏮ السابق", callback_data="tsb_prev")],
            [back_btn("main_menu")],
        ])
        await safe_edit(query, msg, reply_markup=kb)
        return

    if data == "tsb_next":
        idx, _ = get_tasbih_session(u.id)
        idx = (idx + 1) % len(TASBIH_LIST)
        save_tasbih_session(u.id, idx, 0)
        phrase, fadl, target = TASBIH_LIST[idx]
        msg = f"📿 *التسبيح* ({idx+1}/{len(TASBIH_LIST)})\n\n*{phrase}*\n\n💡 _{fadl}_\n\nالعدد: *0* / {target}"
        kb  = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ تسبيحة", callback_data="tsb_inc"),
             InlineKeyboardButton("🔄 تصفير",  callback_data="tsb_reset")],
            [InlineKeyboardButton("⏭ التالي",  callback_data="tsb_next"),
             InlineKeyboardButton("⏮ السابق", callback_data="tsb_prev")],
            [InlineKeyboardButton("📊 إحصائياتي", callback_data="tsb_stats")],
            [back_btn("main_menu")],
        ])
        await safe_edit(query, msg, reply_markup=kb)
        return

    if data == "tsb_prev":
        idx, _ = get_tasbih_session(u.id)
        idx = (idx - 1) % len(TASBIH_LIST)
        save_tasbih_session(u.id, idx, 0)
        phrase, fadl, target = TASBIH_LIST[idx]
        msg = f"📿 *التسبيح* ({idx+1}/{len(TASBIH_LIST)})\n\n*{phrase}*\n\n💡 _{fadl}_\n\nالعدد: *0* / {target}"
        kb  = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ تسبيحة", callback_data="tsb_inc"),
             InlineKeyboardButton("🔄 تصفير",  callback_data="tsb_reset")],
            [InlineKeyboardButton("⏭ التالي",  callback_data="tsb_next"),
             InlineKeyboardButton("⏮ السابق", callback_data="tsb_prev")],
            [InlineKeyboardButton("📊 إحصائياتي", callback_data="tsb_stats")],
            [back_btn("main_menu")],
        ])
        await safe_edit(query, msg, reply_markup=kb)
        return

    if data == "tsb_stats":
        total, rows = get_tasbih_stats(u.id)
        lines = "\n".join([f"  • {p}: {c}" for p, c in rows]) if rows else "لا توجد بيانات بعد."
        msg   = f"📊 *إحصائيات التسبيح*\n\nإجمالي: *{total}*\n\n🔝 الأكثر:\n{lines}"
        kb    = InlineKeyboardMarkup([[back_btn("main_menu")]])
        await safe_edit(query, msg, reply_markup=kb)
        return

    # ── Adhkar callbacks ───────────────────────────────────────────
    ADHKAR_MAP = {
        "morning_adhkar": ("🌅 أذكار الصباح", MORNING_ADHKAR),
        "evening_adhkar": ("🌆 أذكار المساء", EVENING_ADHKAR),
        "sleep_adhkar":   ("🌙 أذكار النوم",   SLEEP_ADHKAR),
        "wakeup_adhkar":  ("🌺 أذكار الاستيقاظ", WAKEUP_ADHKAR),
        "wudu_adhkar":    ("💧 أذكار الوضوء",  WUDU_ADHKAR),
    }

    if data.startswith("adhkar_done_") or data.startswith("adhkar_next_") or data.startswith("adhkar_prev_"):
        parts  = data.split("_", 3)
        action = parts[1]  # done / next / prev
        key    = parts[2]
        idx    = int(parts[3])
        title, adhkar_list = ADHKAR_MAP.get(key, ("أذكار", []))
        total  = len(adhkar_list)
        if action == "done" or action == "next":
            new_idx = idx + 1
        else:
            new_idx = max(0, idx - 1)
        save_adhkar_progress(u.id, key, new_idx)
        if new_idx >= total:
            custom_btns = get_custom_buttons(key)
            rows = [[InlineKeyboardButton(lb, callback_data=f"custbtn_{bid}")] for bid, lb, _ in custom_btns]
            rows.append([InlineKeyboardButton("🔄 إعادة من البداية", callback_data=f"adhkar_restart_{key}")])
            rows.append([back_btn("main_menu")])
            await safe_edit(query, f"✅ *{title}*\n\nأتممت جميع الأذكار بارك الله فيك! 🌟\n\n{random.choice(MOTIVATION_MSGS)}", reply_markup=InlineKeyboardMarkup(rows))
            return
        dhikr, source, target = adhkar_list[new_idx]
        text = (
            f"*{title}*\n\n"
            f"📿 *{new_idx+1}/{total}*\n\n"
            f"{dhikr}\n\n"
            f"📖 _{source}_\n"
            f"🔢 العدد المطلوب: *{target}*"
        )
        custom_btns = get_custom_buttons(key)
        extra_rows  = [[InlineKeyboardButton(lb, callback_data=f"custbtn_{bid}")] for bid, lb, _ in custom_btns]
        kb_rows = [
            [InlineKeyboardButton("✅ تم", callback_data=f"adhkar_done_{key}_{new_idx}"),
             InlineKeyboardButton("⏭ التالي", callback_data=f"adhkar_next_{key}_{new_idx}")],
            [InlineKeyboardButton("⏮ السابق", callback_data=f"adhkar_prev_{key}_{new_idx}"),
             InlineKeyboardButton("🔄 إعادة", callback_data=f"adhkar_restart_{key}")],
        ] + extra_rows + [[back_btn("main_menu")]]
        await safe_edit(query, text, reply_markup=InlineKeyboardMarkup(kb_rows))
        return

    if data.startswith("adhkar_restart_"):
        key = data.split("_", 2)[2]
        reset_adhkar_progress(u.id, key)
        title, adhkar_list = ADHKAR_MAP.get(key, ("أذكار", []))
        if adhkar_list:
            dhikr, source, target = adhkar_list[0]
            text = (
                f"*{title}*\n\n"
                f"📿 *1/{len(adhkar_list)}*\n\n"
                f"{dhikr}\n\n"
                f"📖 _{source}_\n"
                f"🔢 العدد المطلوب: *{target}*"
            )
            custom_btns = get_custom_buttons(key)
            extra_rows  = [[InlineKeyboardButton(lb, callback_data=f"custbtn_{bid}")] for bid, lb, _ in custom_btns]
            kb_rows = [
                [InlineKeyboardButton("✅ تم", callback_data=f"adhkar_done_{key}_0"),
                 InlineKeyboardButton("⏭ التالي", callback_data=f"adhkar_next_{key}_0")],
                [InlineKeyboardButton("⏮ السابق", callback_data=f"adhkar_prev_{key}_0"),
                 InlineKeyboardButton("🔄 إعادة", callback_data=f"adhkar_restart_{key}")],
            ] + extra_rows + [[back_btn("main_menu")]]
            await safe_edit(query, text, reply_markup=InlineKeyboardMarkup(kb_rows))
        return

    # ── Prayer adhkar ──────────────────────────────────────────────
    if data.startswith("padh_"):
        idx  = int(data.split("_")[1])
        keys = list(PRAYER_ADHKAR.keys())
        key  = keys[idx]
        items = PRAYER_ADHKAR[key]
        text  = f"🕌 *{key}*\n\n"
        for i, (dhikr, src, tgt) in enumerate(items, 1):
            text += f"*{i}.* {dhikr}\n📖 _{src}_\n🔢 {tgt} مرة\n\n"
        custom_btns = get_custom_buttons("prayer_adhkar")
        extra_rows  = [[InlineKeyboardButton(lb, callback_data=f"custbtn_{bid}")] for bid, lb, _ in custom_btns]
        kb_rows = extra_rows + [[back_btn("main_menu")]]
        await safe_edit(query, text, reply_markup=InlineKeyboardMarkup(kb_rows))
        return

    # ── Special duas ───────────────────────────────────────────────
    if data.startswith("sdua_"):
        idx  = int(data.split("_")[1])
        keys = list(SPECIAL_DUAS.keys())
        key  = keys[idx]
        items = SPECIAL_DUAS[key]
        text  = f"🌺 *{key}*\n\n"
        for i, (dua, src, tgt) in enumerate(items, 1):
            text += f"*{i}.* {dua}\n📖 _{src}_\n🔢 {tgt} مرة\n\n"
        custom_btns = get_custom_buttons("special_duas")
        extra_rows  = [[InlineKeyboardButton(lb, callback_data=f"custbtn_{bid}")] for bid, lb, _ in custom_btns]
        kb_rows = extra_rows + [[back_btn("main_menu")]]
        await safe_edit(query, text, reply_markup=InlineKeyboardMarkup(kb_rows))
        return

    # ── Woman adhkar ───────────────────────────────────────────────
    if data.startswith("wadh_"):
        idx  = int(data.split("_")[1])
        keys = list(WOMAN_ADHKAR.keys())
        key  = keys[idx]
        items = WOMAN_ADHKAR[key]
        text  = f"🌸 *{key}*\n\n"
        for i, (dhikr, src, tgt) in enumerate(items, 1):
            text += f"*{i}.* {dhikr}\n📖 _{src}_\n🔢 {tgt} مرة\n\n"
        custom_btns = get_custom_buttons("woman_adhkar")
        extra_rows  = [[InlineKeyboardButton(lb, callback_data=f"custbtn_{bid}")] for bid, lb, _ in custom_btns]
        kb_rows = extra_rows + [[back_btn("main_menu")]]
        await safe_edit(query, text, reply_markup=InlineKeyboardMarkup(kb_rows))
        return

    # ── Friday ─────────────────────────────────────────────────────
    if data.startswith("fri_"):
        sub = data[4:]
        if sub == "surahs":
            text = "📖 *سور الجمعة المستحبة:*\n\n"
            for num, desc in FRIDAY_SURAHS.items():
                text += f"• {desc}\n"
            await safe_edit(query, text, reply_markup=InlineKeyboardMarkup([[back_btn("main_menu")]]))
        else:
            idx = int(sub)
            s   = FRIDAY_SUNNAN[idx]
            text = f"⭐ *{s['title']}*\n\n{s['text']}\n\n📖 _{s['source']}_"
            await safe_edit(query, text, reply_markup=InlineKeyboardMarkup([[back_btn("main_menu")]]))
        return

    # ── Custom button content ──────────────────────────────────────
    if data.startswith("custbtn_"):
        btn_id = int(data.split("_")[1])
        btn    = get_button_by_id(btn_id)
        if not btn:
            await query.answer("⚠️ الزر غير موجود", show_alert=True)
            return
        _, section, label, content = btn
        kb = InlineKeyboardMarkup([[back_btn("main_menu")]])
        await safe_edit(query, f"*{label}*\n\n{content}", reply_markup=kb)
        return

    # ══════════════════════════════════════════════════════════════
    # ADMIN CALLBACKS
    # ══════════════════════════════════════════════════════════════
    if not is_admin(u.id):
        await query.answer("⛔ ليس لديك صلاحية.", show_alert=True)
        return

    # ── Admin: reply to inquiry ────────────────────────────────────
    if data.startswith("adm_reply_"):
        iid = int(data.split("_")[2])
        con = sqlite3.connect(DB_PATH)
        row = con.execute("SELECT user_id, first_name, message FROM inquiries WHERE id=?", (iid,)).fetchone()
        con.close()
        if not row:
            await query.answer("⚠️ لم يُعثر على الاستفسار", show_alert=True)
            return
        context.user_data["state"]     = "awaiting_admin_reply"
        context.user_data["reply_iid"] = iid
        context.user_data["reply_uid"] = row[0]
        await safe_edit(query,
            f"↩️ *الرد على استفسار #{iid}*\n\n"
            f"👤 {row[1]}\n💬 {row[2]}\n\n"
            f"اكتب ردك الآن أو /start للإلغاء:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="adm_cancel_reply")]])
        )
        return

    if data == "adm_cancel_reply":
        context.user_data.clear()
        await safe_edit(query, "❌ تم إلغاء الرد.", reply_markup=build_admin_keyboard())
        return

    # ── Admin: pending inquiries ───────────────────────────────────
    if data == "adm_inquiries":
        rows = get_pending_inquiries()
        if not rows:
            await safe_edit(query, "✅ لا توجد استفسارات معلقة.", reply_markup=build_admin_keyboard())
            return
        btns = []
        text = "📋 *الاستفسارات المعلقة:*\n\n"
        for iid, uid_, uname, fname, msg, created in rows:
            text += f"*#{iid}* — {fname} (@{uname or '—'})\n💬 {msg[:80]}...\n⏰ {created[:16]}\n\n"
            btns.append([InlineKeyboardButton(f"↩️ رد على #{iid}", callback_data=f"adm_reply_{iid}")])
        btns.append([back_btn("adm_panel")])
        await safe_edit(query, text, reply_markup=InlineKeyboardMarkup(btns))
        return

    if data == "adm_panel":
        await safe_edit(query, "⚙️ *لوحة الإدارة*", reply_markup=build_admin_keyboard())
        return

    # ── Admin: all inquiries ───────────────────────────────────────
    if data == "adm_all_inquiries":
        rows = get_all_inquiries(20)
        if not rows:
            await safe_edit(query, "لا توجد استفسارات.", reply_markup=build_admin_keyboard())
            return
        text = "📜 *كل الاستفسارات (آخر 20):*\n\n"
        btns = []
        for iid, uid_, uname, fname, msg, status, created in rows:
            emoji = "✅" if status == "replied" else "⏳"
            text  += f"{emoji} *#{iid}* — {fname}\n💬 {msg[:60]}...\n\n"
            if status == "pending":
                btns.append([InlineKeyboardButton(f"↩️ رد على #{iid}", callback_data=f"adm_reply_{iid}")])
        btns.append([back_btn("adm_panel")])
        await safe_edit(query, text, reply_markup=InlineKeyboardMarkup(btns))
        return

    # ── Admin: add hadith ──────────────────────────────────────────
    if data == "adm_add_hadith":
        context.user_data["state"] = "awaiting_add_hadith"
        await safe_edit(query, "➕ أرسل الحديث بالصيغة:\n`نص الحديث | المصدر`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="adm_panel")]]))
        return

    if data == "adm_del_hadith":
        con  = sqlite3.connect(DB_PATH)
        rows = con.execute("SELECT id, text FROM hadiths ORDER BY id DESC LIMIT 10").fetchall()
        con.close()
        if not rows:
            await safe_edit(query, "لا توجد أحاديث.", reply_markup=build_admin_keyboard())
            return
        btns = [[InlineKeyboardButton(f"🗑 #{r[0]}: {r[1][:40]}...", callback_data=f"adm_delh_{r[0]}")] for r in rows]
        btns.append([back_btn("adm_panel")])
        await safe_edit(query, "🗑 اختر الحديث للحذف:", reply_markup=InlineKeyboardMarkup(btns))
        return

    if data.startswith("adm_delh_"):
        hid = int(data.split("_")[2])
        con = sqlite3.connect(DB_PATH)
        con.execute("DELETE FROM hadiths WHERE id=?", (hid,))
        con.commit(); con.close()
        await safe_edit(query, f"✅ تم حذف الحديث #{hid}.", reply_markup=build_admin_keyboard())
        return

    # ── Admin: add dua ─────────────────────────────────────────────
    if data == "adm_add_dua":
        context.user_data["state"] = "awaiting_add_dua"
        await safe_edit(query, "➕ أرسل الدعاء بالصيغة:\n`نص الدعاء | المصدر`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="adm_panel")]]))
        return

    if data == "adm_del_dua":
        con  = sqlite3.connect(DB_PATH)
        rows = con.execute("SELECT id, text FROM duas ORDER BY id DESC LIMIT 10").fetchall()
        con.close()
        if not rows:
            await safe_edit(query, "لا توجد أدعية.", reply_markup=build_admin_keyboard())
            return
        btns = [[InlineKeyboardButton(f"🗑 #{r[0]}: {r[1][:40]}...", callback_data=f"adm_deld_{r[0]}")] for r in rows]
        btns.append([back_btn("adm_panel")])
        await safe_edit(query, "🗑 اختر الدعاء للحذف:", reply_markup=InlineKeyboardMarkup(btns))
        return

    if data.startswith("adm_deld_"):
        did = int(data.split("_")[2])
        con = sqlite3.connect(DB_PATH)
        con.execute("DELETE FROM duas WHERE id=?", (did,))
        con.commit(); con.close()
        await safe_edit(query, f"✅ تم حذف الدعاء #{did}.", reply_markup=build_admin_keyboard())
        return

    # ── Admin: add content ─────────────────────────────────────────
    if data == "adm_add_content":
        context.user_data["state"] = "awaiting_add_content"
        await safe_edit(query, "➕ أرسل المحتوى بالصيغة:\n`التصنيف | النص | المصدر`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="adm_panel")]]))
        return

    if data == "adm_del_content":
        con  = sqlite3.connect(DB_PATH)
        rows = con.execute("SELECT id, category, text FROM bot_content ORDER BY id DESC LIMIT 10").fetchall()
        con.close()
        if not rows:
            await safe_edit(query, "لا يوجد محتوى.", reply_markup=build_admin_keyboard())
            return
        btns = [[InlineKeyboardButton(f"🗑 [{r[1]}] {r[2][:35]}...", callback_data=f"adm_delc_{r[0]}")] for r in rows]
        btns.append([back_btn("adm_panel")])
        await safe_edit(query, "🗑 اختر المحتوى للحذف:", reply_markup=InlineKeyboardMarkup(btns))
        return

    if data.startswith("adm_delc_"):
        cid = int(data.split("_")[2])
        con = sqlite3.connect(DB_PATH)
        con.execute("DELETE FROM bot_content WHERE id=?", (cid,))
        con.commit(); con.close()
        await safe_edit(query, f"✅ تم حذف المحتوى #{cid}.", reply_markup=build_admin_keyboard())
        return

    # ── Admin: add/del admin ───────────────────────────────────────
    if data == "adm_add_admin":
        context.user_data["state"] = "awaiting_add_admin"
        await safe_edit(query, "👤 أرسل معرّف المستخدم (ID رقمي) لترقيته مشرفاً:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="adm_panel")]]))
        return

    if data == "adm_del_admin":
        context.user_data["state"] = "awaiting_del_admin"
        await safe_edit(query, "❌ أرسل معرّف المشرف لإزالة صلاحياته:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="adm_panel")]]))
        return

    # ── Admin: ban/unban ───────────────────────────────────────────
    if data == "adm_ban":
        context.user_data["state"] = "awaiting_ban"
        await safe_edit(query, "🚫 أرسل معرّف المستخدم لحظره:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="adm_panel")]]))
        return

    if data == "adm_unban":
        context.user_data["state"] = "awaiting_unban"
        await safe_edit(query, "✅ أرسل معرّف المستخدم لرفع الحظر عنه:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="adm_panel")]]))
        return

    # ── Admin: send user / broadcast ──────────────────────────────
    if data == "adm_send_user":
        context.user_data["state"] = "awaiting_send_user"
        await safe_edit(query, "📩 أرسل بالصيغة:\n`معرف_المستخدم | الرسالة`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="adm_panel")]]))
        return

    if data == "adm_broadcast":
        context.user_data["state"] = "awaiting_broadcast"
        await safe_edit(query, "📢 أرسل رسالة البث للجميع:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="adm_panel")]]))
        return

    # ── Admin: users list ──────────────────────────────────────────
    if data == "adm_users_list":
        rows = get_users_list(30)
        text = "👥 *قائمة المستخدمين (آخر 30):*\n\n"
        for uid_, uname, fname, is_adm, is_ban, last in rows:
            role  = "👑" if uid_ in SUPER_ADMINS else ("🔧" if is_adm else "👤")
            badge = "🚫" if is_ban else ""
            text += f"{role}{badge} {fname or '—'} (@{uname or '—'}) `{uid_}`\n"
        await safe_edit(query, text, reply_markup=InlineKeyboardMarkup([[back_btn("adm_panel")]]))
        return

    # ── Admin: stats ───────────────────────────────────────────────
    if data == "adm_stats":
        s = get_admin_stats()
        text = (
            f"📊 *إحصائيات البوت*\n\n"
            f"👥 المستخدمون: {s['users']}\n"
            f"🔧 المشرفون: {s['admins']}\n"
            f"🚫 المحظورون: {s['banned']}\n"
            f"🟢 نشطون اليوم: {s['active_today']}\n\n"
            f"📚 الأحاديث: {s['hadiths']}\n"
            f"🤲 الأدعية: {s['duas']}\n"
            f"📄 المحتوى: {s['content']}\n\n"
            f"📿 إجمالي التسبيح: {s['tasbih_total']}\n\n"
            f"💬 الاستفسارات:\n"
            f"  ⏳ معلقة: {s['pending']}\n"
            f"  ✅ مُجاب عليها: {s['replied']}"
        )
        await safe_edit(query, text, reply_markup=InlineKeyboardMarkup([[back_btn("adm_panel")]]))
        return

    # ══════════════════════════════════════════════════════════════
    # ADMIN: CUSTOM BUTTONS MANAGEMENT
    # ══════════════════════════════════════════════════════════════
    if data == "adm_custom_btns":
        rows_kb = []
        for sec_key, sec_name in SECTIONS.items():
            custom = get_custom_buttons(sec_key)
            count  = len(custom)
            rows_kb.append([InlineKeyboardButton(
                f"{'🔘' if count else '⬜'} {sec_name} ({count})",
                callback_data=f"adm_sec_{sec_key}"
            )])
        rows_kb.append([back_btn("adm_panel")])
        await safe_edit(query, "🔘 *إدارة الأزرار المخصصة*\n\nاختر القسم:", reply_markup=InlineKeyboardMarkup(rows_kb))
        return

    if data.startswith("adm_sec_"):
        section = data[8:]
        sec_name = SECTIONS.get(section, section)
        custom   = get_custom_buttons(section)
        text     = f"🔘 *{sec_name}*\n\nالأزرار الموجودة: {len(custom)}\n\n"
        rows_kb  = []
        for bid, label, content in custom:
            text += f"• *{label}*: {content[:50]}...\n"
            rows_kb.append([
                InlineKeyboardButton(f"👁 {label}", callback_data=f"adm_viewbtn_{bid}"),
                InlineKeyboardButton("🗑 حذف",      callback_data=f"adm_delbtn_{bid}")
            ])
        rows_kb.append([InlineKeyboardButton("➕ إضافة زر جديد", callback_data=f"adm_addbtn_{section}")])
        rows_kb.append([back_btn("adm_custom_btns")])
        await safe_edit(query, text or f"🔘 *{sec_name}*\n\nلا توجد أزرار بعد.", reply_markup=InlineKeyboardMarkup(rows_kb))
        return

    if data.startswith("adm_addbtn_"):
        section = data[11:]
        sec_name = SECTIONS.get(section, section)
        context.user_data["state"]          = "awaiting_custom_btn_label"
        context.user_data["new_btn_section"] = section
        await safe_edit(query,
            f"➕ *إضافة زر جديد في: {sec_name}*\n\n"
            f"أرسل الآن *اسم الزر* (النص الذي سيظهر على الزر):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data=f"adm_sec_{section}")]])
        )
        return

    if data.startswith("adm_viewbtn_"):
        btn_id = int(data.split("_")[2])
        btn    = get_button_by_id(btn_id)
        if not btn:
            await query.answer("⚠️ الزر غير موجود", show_alert=True)
            return
        _, section, label, content = btn
        sec_name = SECTIONS.get(section, section)
        await safe_edit(query,
            f"👁 *معاينة الزر*\n\n"
            f"📂 القسم: {sec_name}\n"
            f"🔘 الاسم: {label}\n\n"
            f"📝 المحتوى:\n{content}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑 حذف الزر", callback_data=f"adm_delbtn_{btn_id}")],
                [back_btn(f"adm_sec_{section}")]
            ])
        )
        return

    if data.startswith("adm_delbtn_"):
        btn_id  = int(data.split("_")[2])
        btn     = get_button_by_id(btn_id)
        if not btn:
            await query.answer("⚠️ الزر غير موجود", show_alert=True)
            return
        section = btn[1]
        delete_custom_button(btn_id)
        sec_name = SECTIONS.get(section, section)
        # Refresh section view
        custom   = get_custom_buttons(section)
        text     = f"✅ تم حذف الزر.\n\n🔘 *{sec_name}*\n\nالأزرار المتبقية: {len(custom)}\n\n"
        rows_kb  = []
        for bid, label, content in custom:
            text += f"• *{label}*: {content[:50]}\n"
            rows_kb.append([
                InlineKeyboardButton(f"👁 {label}", callback_data=f"adm_viewbtn_{bid}"),
                InlineKeyboardButton("🗑 حذف",      callback_data=f"adm_delbtn_{bid}")
            ])
        rows_kb.append([InlineKeyboardButton("➕ إضافة زر جديد", callback_data=f"adm_addbtn_{section}")])
        rows_kb.append([back_btn("adm_custom_btns")])
        await safe_edit(query, text, reply_markup=InlineKeyboardMarkup(rows_kb))
        return

    # Fallback
    await query.answer()

# ══════════════════════════════════════════════════════════════════
# SCHEDULED NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════
async def send_morning_reminder(context):
    users = get_all_users()
    for uid_ in users:
        if not notif_already_sent(uid_, "morning"):
            try:
                await context.bot.send_message(uid_, "🌅 *أذكار الصباح*\nلا تنسَ أذكار الصباح! اضغط على القائمة واختر 🌅 أذكار الصباح", parse_mode=ParseMode.MARKDOWN)
                mark_notif_sent(uid_, "morning")
            except: pass

async def send_evening_reminder(context):
    users = get_all_users()
    for uid_ in users:
        if not notif_already_sent(uid_, "evening"):
            try:
                await context.bot.send_message(uid_, "🌆 *أذكار المساء*\nحان وقت أذكار المساء! اضغط على القائمة واختر 🌆 أذكار المساء", parse_mode=ParseMode.MARKDOWN)
                mark_notif_sent(uid_, "evening")
            except: pass

async def send_friday_reminder(context):
    now = datetime.now()
    if now.weekday() == 4:  # Friday
        users = get_all_users()
        for uid_ in users:
            if not notif_already_sent(uid_, "friday"):
                try:
                    await context.bot.send_message(uid_, "⭐ *يوم الجمعة المبارك*\nلا تنسَ سنن الجمعة والصلاة على النبي ﷺ وقراءة سورة الكهف!", parse_mode=ParseMode.MARKDOWN)
                    mark_notif_sent(uid_, "friday")
                except: pass

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

    # Scheduled jobs
    jq = app.job_queue
    if jq:
        jq.run_daily(send_morning_reminder, time=time(5, 30, tzinfo=timezone.utc))
        jq.run_daily(send_evening_reminder, time=time(16, 0, tzinfo=timezone.utc))
        jq.run_daily(send_friday_reminder,  time=time(6, 0,  tzinfo=timezone.utc))

    logger.info("🤖 البوت يعمل...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()المدينة غير موجودة. أرس
