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
    "✨ ما شاء الله! أتممت هذا الذكر. بارك الله فيك.",
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

def cancel_done_btns(done_cb="main_menu", cancel_cb="main_menu"):
    return [InlineKeyboardButton("❌ إلغاء", callback_data=cancel_cb), InlineKeyboardButton("✅ تم", callback_data=done_cb)]

# ══════════════════════════════════════════════════════════════════
# لوحات المفاتيح
# ══════════════════════════════════════════════════════════════════
def get_main_keyboard(uid=None):
    rows = [
        ["📖 القرآن الكريم",     "🌿 الورد اليومي"],
        ["📿 التسبيح",           "🌅 أذكار الصباح"],
        ["🌆 أذكار المساء",      "🌙 أذكار النوم"],
        ["🕌 أذكار الصلاة",     "✨ أذكار الاستيقاظ"],   # ← تم التغيير هنا
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
    if end < 114: nav.append(InlineKeyboardButton("▶️ التالي", callback_data=f"sp_{page+1}_{riwaya}"))
    if nav: rows.append(nav)
    rows.append([back_btn("quran_back")])
    return InlineKeyboardMarkup(rows)

# ── لوحة اختيار الآية بعد اختيار السورة ──────────────────────────
def build_surah_options_keyboard(surah, riwaya):
    """تظهر بعد اختيار السورة: من البداية، من حيث توقفت، اختر آية"""
    last = get_surah_progress_global(surah, riwaya)  # placeholder — يُستدعى مع uid
    return surah, riwaya

def build_surah_start_keyboard(uid, surah, riwaya):
    total = SURAH_AYAH_COUNT.get(surah, 1)
    last  = get_surah_progress(uid, surah, riwaya)
    rows  = []
    rows.append([InlineKeyboardButton("▶️ من البداية", callback_data=f"read_{surah}_1_{riwaya}")])
    if last > 0:
        rows.append([InlineKeyboardButton(f"⏩ من حيث توقفت (آية {last})", callback_data=f"read_{surah}_{last}_{riwaya}")])
    rows.append([InlineKeyboardButton("🔢 اختر آية معينة", callback_data=f"choose_ayah_{surah}_{riwaya}")])
    rows.append([back_btn(f"sp_0_{riwaya}")])
    return InlineKeyboardMarkup(rows)

def build_ayah_choice_keyboard(surah, riwaya, page=0):
    """لوحة اختيار الآية برقمها"""
    total = SURAH_AYAH_COUNT.get(surah, 1)
    per   = 20
    start = page * per + 1
    end   = min(start + per - 1, total)
    rows  = []
    ayahs = list(range(start, end + 1))
    for i in range(0, len(ayahs), 5):
        row = [InlineKeyboardButton(str(a), callback_data=f"read_{surah}_{a}_{riwaya}") for a in ayahs[i:i+5]]
        rows.append(row)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ السابق", callback_data=f"ayah_page_{surah}_{riwaya}_{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton("▶️ التالي", callback_data=f"ayah_page_{surah}_{riwaya}_{page+1}"))
    if nav: rows.append(nav)
    rows.append([back_btn(f"ss_{surah}_{riwaya}")])
    return InlineKeyboardMarkup(rows)

def build_city_keyboard():
    rows = []
    for i in range(0, len(ALGERIAN_CITIES), 3):
        rows.append([InlineKeyboardButton(c, callback_data=f"city_{c}") for c in ALGERIAN_CITIES[i:i+3]])
    rows.append([back_btn("main_menu")])
    return InlineKeyboardMarkup(rows)

def build_friday_keyboard():
    rows = []
    for surah_num, desc in FRIDAY_SURAHS.items():
        rows.append([InlineKeyboardButton(f"📖 {desc[:50]}", callback_data=f"friday_surah_{surah_num}")])
    for i, s in enumerate(FRIDAY_SUNNAN):
        rows.append([InlineKeyboardButton(f"⭐ {s['title']}", callback_data=f"friday_info_{i}")])
    rows.append([back_btn("main_menu")])
    return InlineKeyboardMarkup(rows)

def build_tasbih_list_keyboard():
    rows = []
    for i, (phrase, fad, req) in enumerate(TASBIH_LIST):
        rows.append([InlineKeyboardButton(f"📿 {phrase[:20]}... ({req})", callback_data=f"tsb_start_{i}")])
    rows.append([back_btn("main_menu")])
    return InlineKeyboardMarkup(rows)

def build_tasbih_counter_keyboard(phrase_idx, counter, required):
    phrase, fad, req = TASBIH_LIST[phrase_idx]
    rows = []
    if counter < req:
        rows.append([InlineKeyboardButton(f"📿 تسبيح ({counter}/{req})", callback_data=f"tsb_count_{phrase_idx}_{counter}")])
    else:
        rows.append([InlineKeyboardButton("✅ تم الانتهاء", callback_data=f"tsb_done_{phrase_idx}")])
    rows.append([
        InlineKeyboardButton("💾 حفظ التقدم", callback_data=f"tsb_save_{phrase_idx}_{counter}"),
        InlineKeyboardButton("🔄 إعادة من البداية", callback_data=f"tsb_reset_{phrase_idx}"),
    ])
    rows.append([
        InlineKeyboardButton("📋 قائمة التسابيح", callback_data="tasbih_list"),
        back_btn("main_menu"),
    ])
    return InlineKeyboardMarkup(rows)

def build_adhkar_nav(key, lst, idx, counter):
    item_text, item_src, item_req = lst[idx]
    total = len(lst)
    rows  = []
    if item_req > 1 and counter < item_req:
        rows.append([InlineKeyboardButton(f"📿 تسبيح ({counter}/{item_req})", callback_data=f"adhkar_count_{key}_{idx}_{counter+1}")])
    elif idx < total - 1:
        rows.append([InlineKeyboardButton("▶️ التالي", callback_data=f"adhkar_next_{key}_{idx+1}_0")])
    else:
        rows.append([InlineKeyboardButton("✅ تم — اتممت جميع الأذكار", callback_data=f"adhkar_done_{key}")])
    rows.append([
        InlineKeyboardButton("💾 حفظ التقدم", callback_data=f"adhkar_save_{key}_{idx}_{counter}"),
        InlineKeyboardButton("🔄 إعادة من البداية", callback_data=f"adhkar_restart_{key}"),
    ])
    rows.append([
        InlineKeyboardButton("❌ إلغاء", callback_data="main_menu"),
        back_btn("main_menu"),
    ])
    return InlineKeyboardMarkup(rows)

def build_prayer_adhkar_keyboard():
    rows = [[InlineKeyboardButton(f"🕌 {k}", callback_data=f"pr_adhkar_{k}")] for k in PRAYER_ADHKAR.keys()]
    rows.append([back_btn("main_menu")])
    return InlineKeyboardMarkup(rows)

def build_special_duas_keyboard():
    rows = [[InlineKeyboardButton(f"🤲 {k}", callback_data=f"sdua_{i}")] for i, k in enumerate(SPECIAL_DUAS.keys())]
    rows.append([back_btn("main_menu")])
    return InlineKeyboardMarkup(rows)

def build_woman_adhkar_keyboard():
    rows = [[InlineKeyboardButton(f"🌸 {k}", callback_data=f"wad_{i}")] for i, k in enumerate(WOMAN_ADHKAR.keys())]
    rows.append([back_btn("main_menu")])
    return InlineKeyboardMarkup(rows)

# ══════════════════════════════════════════════════════════════════
# عرض الأذكار ذكراً بذكر
# ══════════════════════════════════════════════════════════════════
async def show_adhkar_item(query, key, lst, idx, counter=0):
    item_text, item_src, item_req = lst[idx]
    total = len(lst)
    progress = f"({idx+1}/{total})"
    counter_text = f"\n\n📿 *العداد:* {counter}/{item_req}" if item_req > 1 else ""
    text = (
        f"📿 *ذكر {progress}*\n\n"
        f"{item_text}\n\n"
        f"_📌 {item_src}_{counter_text}"
    )
    kb = build_adhkar_nav(key, lst, idx, counter)
    await safe_edit(query, text, reply_markup=kb)

ADHKAR_MAP = {
    "morning":  ("🌅 أذكار الصباح",   MORNING_ADHKAR),
    "evening":  ("🌆 أذكار المساء",    EVENING_ADHKAR),
    "sleep":    ("🌙 أذكار النوم",     SLEEP_ADHKAR),
    "wakeup":   ("📿 أذكار الاستيقاظ", WAKEUP_ADHKAR),   # ← تم التغيير هنا
    "wudu":     ("💧 أذكار الوضوء",    WUDU_ADHKAR),
}

# ══════════════════════════════════════════════════════════════════
# Handlers — Commands
# ══════════════════════════════════════════════════════════════════
@banned_check
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    user = update.effective_user
    upsert_user(uid, user.username, user.first_name, user.last_name)
    log_activity(uid, "start")
    text = (
                "🕌 *بسم الله الرحمن الرحيم*\n\n"
        "السلام عليكم ورحمة الله وبركاته 🌿\n\n"
        "أهلاً بك في *بوت المسلم* 📖\n\n"
        "يمكنك من خلال هذا البوت:\n"
        "• قراءة القرآن الكريم (حفص وورش)\n"
        "• متابعة وردك اليومي\n"
        "• أذكار الصباح والمساء والنوم والاستيقاظ\n"
        "• التسبيح والأدعية\n"
        "• أوقات الصلاة لمدن الجزائر\n"
        "• وأكثر...\n\n"
        "اختر من القائمة أدناه 👇"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(uid))

@banned_check
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    text = (
        "ℹ️ *المساعدة*\n\n"
        "📖 *القرآن الكريم* — اقرأ بروايتي حفص وورش مع حفظ تقدمك\n"
        "🌿 *الورد اليومي* — ورد قرآني يومي متواصل\n"
        "📿 *التسبيح* — عداد التسبيح مع حفظ الإحصائيات\n"
        "🌅 *أذكار الصباح والمساء* — بالمأثورات الصحيحة\n"
        "🌙 *أذكار النوم والاستيقاظ* — سنة النبي ﷺ\n"
        "🕌 *أذكار الصلاة* — من الأذان حتى ما بعد الصلاة\n"
        "💧 *أذكار الوضوء* — أذكار البدء والانتهاء\n"
        "🤲 *أدعية خاصة* — للهم والكرب والشفاء والرزق\n"
        "🌸 *أحكام المرأة* — أدعية مخصصة\n"
        "⭐ *سنن الجمعة* — سور وسنن يوم الجمعة\n"
        "🕐 *أوقات الصلاة* — لجميع مدن الجزائر\n"
        "📅 *التاريخ* — هجري وميلادي\n"
        "💬 *استفسار* — تواصل مع الإدارة\n\n"
        "بارك الله فيك 🌿"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(uid))

# ══════════════════════════════════════════════════════════════════
# Handler — Messages
# ══════════════════════════════════════════════════════════════════
@banned_check
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    user = update.effective_user
    upsert_user(uid, user.username, user.first_name, user.last_name)
    txt  = update.message.text.strip()

    # ── حالات الانتظار ──────────────────────────────────────────
    state = context.user_data.get("awaiting")

    if state == "inquiry":
        context.user_data.pop("awaiting", None)
        iid = save_inquiry(uid, user.username, user.first_name, txt)
        log_activity(uid, "inquiry", str(iid))
        await update.message.reply_text(
            "✅ *تم إرسال استفسارك بنجاح!*\n\nسيرد عليك المشرف قريباً إن شاء الله 🌿",
            parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(uid))
        for adm in get_all_admins():
            try:
                await context.bot.send_message(
                    adm,
                    f"📨 *استفسار جديد #{iid}*\n"
                    f"👤 {user.first_name} (@{user.username})\n\n"
                    f"💬 {txt}",
                    parse_mode=ParseMode.MARKDOWN)
            except: pass
        return

    if state == "adm_add_hadith":
        context.user_data.pop("awaiting", None)
        parts = txt.split("|", 1)
        if len(parts) < 2:
            await update.message.reply_text("⚠️ الصيغة: نص الحديث | المصدر", reply_markup=get_main_keyboard(uid)); return
        con = sqlite3.connect(DB_PATH)
        con.execute("INSERT INTO hadiths (text, source, added_by) VALUES (?,?,?)", (parts[0].strip(), parts[1].strip(), uid))
        con.commit(); con.close()
        await update.message.reply_text("✅ تم إضافة الحديث.", reply_markup=get_main_keyboard(uid)); return

    if state == "adm_add_dua":
        context.user_data.pop("awaiting", None)
        parts = txt.split("|", 1)
        if len(parts) < 2:
            await update.message.reply_text("⚠️ الصيغة: نص الدعاء | المصدر", reply_markup=get_main_keyboard(uid)); return
        con = sqlite3.connect(DB_PATH)
        con.execute("INSERT INTO duas (text, source, added_by) VALUES (?,?,?)", (parts[0].strip(), parts[1].strip(), uid))
        con.commit(); con.close()
        await update.message.reply_text("✅ تم إضافة الدعاء.", reply_markup=get_main_keyboard(uid)); return

    if state == "adm_del_hadith":
        context.user_data.pop("awaiting", None)
        try:
            hid = int(txt)
            con = sqlite3.connect(DB_PATH)
            con.execute("DELETE FROM hadiths WHERE id=?", (hid,)); con.commit(); con.close()
            await update.message.reply_text(f"✅ تم حذف الحديث #{hid}.", reply_markup=get_main_keyboard(uid))
        except:
            await update.message.reply_text("⚠️ أرسل رقم الحديث الصحيح.", reply_markup=get_main_keyboard(uid))
        return

    if state == "adm_del_dua":
        context.user_data.pop("awaiting", None)
        try:
            did = int(txt)
            con = sqlite3.connect(DB_PATH)
            con.execute("DELETE FROM duas WHERE id=?", (did,)); con.commit(); con.close()
            await update.message.reply_text(f"✅ تم حذف الدعاء #{did}.", reply_markup=get_main_keyboard(uid))
        except:
            await update.message.reply_text("⚠️ أرسل رقم الدعاء الصحيح.", reply_markup=get_main_keyboard(uid))
        return

    if state == "adm_add_content":
        context.user_data.pop("awaiting", None)
        parts = txt.split("|", 2)
        if len(parts) < 3:
            await update.message.reply_text("⚠️ الصيغة: التصنيف | النص | المصدر", reply_markup=get_main_keyboard(uid)); return
        con = sqlite3.connect(DB_PATH)
        con.execute("INSERT INTO bot_content (category, text, source, added_by) VALUES (?,?,?,?)", (parts[0].strip(), parts[1].strip(), parts[2].strip(), uid))
        con.commit(); con.close()
        await update.message.reply_text("✅ تم إضافة المحتوى.", reply_markup=get_main_keyboard(uid)); return

    if state == "adm_del_content":
        context.user_data.pop("awaiting", None)
        try:
            cid = int(txt)
            con = sqlite3.connect(DB_PATH)
            con.execute("DELETE FROM bot_content WHERE id=?", (cid,)); con.commit(); con.close()
            await update.message.reply_text(f"✅ تم حذف المحتوى #{cid}.", reply_markup=get_main_keyboard(uid))
        except:
            await update.message.reply_text("⚠️ أرسل رقم المحتوى الصحيح.", reply_markup=get_main_keyboard(uid))
        return

    if state == "adm_add_admin":
        context.user_data.pop("awaiting", None)
        try:
            new_adm = int(txt)
            con = sqlite3.connect(DB_PATH)
            con.execute("UPDATE users SET is_admin=1 WHERE user_id=?", (new_adm,)); con.commit(); con.close()
            await update.message.reply_text(f"✅ تم تعيين {new_adm} مشرفاً.", reply_markup=get_main_keyboard(uid))
        except:
            await update.message.reply_text("⚠️ أرسل ID صحيح.", reply_markup=get_main_keyboard(uid))
        return

    if state == "adm_del_admin":
        context.user_data.pop("awaiting", None)
        try:
            rem_adm = int(txt)
            delete_admin(rem_adm)
            await update.message.reply_text(f"✅ تم إزالة صلاحية {rem_adm}.", reply_markup=get_main_keyboard(uid))
        except:
            await update.message.reply_text("⚠️ أرسل ID صحيح.", reply_markup=get_main_keyboard(uid))
        return

    if state == "adm_ban":
        context.user_data.pop("awaiting", None)
        try:
            ban_uid = int(txt); ban_user(ban_uid)
            await update.message.reply_text(f"✅ تم حظر {ban_uid}.", reply_markup=get_main_keyboard(uid))
        except:
            await update.message.reply_text("⚠️ أرسل ID صحيح.", reply_markup=get_main_keyboard(uid))
        return

    if state == "adm_unban":
        context.user_data.pop("awaiting", None)
        try:
            uban_uid = int(txt); unban_user(uban_uid)
            await update.message.reply_text(f"✅ تم رفع حظر {uban_uid}.", reply_markup=get_main_keyboard(uid))
        except:
            await update.message.reply_text("⚠️ أرسل ID صحيح.", reply_markup=get_main_keyboard(uid))
        return

    if state == "adm_send_user":
        context.user_data["adm_send_msg"] = txt
        context.user_data["awaiting"] = "adm_send_uid"
        await update.message.reply_text("📩 الآن أرسل ID المستخدم:")
        return

    if state == "adm_send_uid":
        msg_to_send = context.user_data.pop("adm_send_msg", "")
        context.user_data.pop("awaiting", None)
        try:
            target_uid = int(txt)
            await context.bot.send_message(target_uid, f"📩 *رسالة من الإدارة:*\n\n{msg_to_send}", parse_mode=ParseMode.MARKDOWN)
            await update.message.reply_text("✅ تم الإرسال.", reply_markup=get_main_keyboard(uid))
        except:
            await update.message.reply_text("⚠️ تعذّر الإرسال. تحقق من ID.", reply_markup=get_main_keyboard(uid))
        return

    if state == "adm_broadcast":
        context.user_data.pop("awaiting", None)
        all_users = get_all_users(); success = 0
        for u in all_users:
            try:
                await context.bot.send_message(u, f"📢 *إعلان من الإدارة:*\n\n{txt}", parse_mode=ParseMode.MARKDOWN)
                success += 1
            except: pass
        await update.message.reply_text(f"✅ تم الإرسال لـ {success}/{len(all_users)}.", reply_markup=get_main_keyboard(uid))
        return

    if state == "adm_reply":
        iid = context.user_data.pop("reply_iid", None)
        context.user_data.pop("awaiting", None)
        if iid:
            target = reply_to_inquiry(iid, txt)
            if target:
                try:
                    await context.bot.send_message(
                        target,
                        f"📨 *رد الإدارة على استفسارك:*\n\n{txt}",
                        parse_mode=ParseMode.MARKDOWN)
                except: pass
            await update.message.reply_text("✅ تم إرسال الرد.", reply_markup=get_main_keyboard(uid))
        return

    # ── القائمة الرئيسية ─────────────────────────────────────────
    log_activity(uid, "menu", txt)

    if txt in ["📖 القرآن الكريم"]:
        await update.message.reply_text(
            "📖 *القرآن الكريم*\n\nاختر رواية القراءة:",
            parse_mode=ParseMode.MARKDOWN, reply_markup=build_quran_keyboard())

    elif txt in ["🌿 الورد اليومي"]:
        surah, ayah = get_wird_progress(uid)
        total_ayahs = SURAH_AYAH_COUNT.get(surah, 286)
        next_ayah   = ayah + 1
        if next_ayah > total_ayahs:
            surah += 1; next_ayah = 1
            if surah > 114: surah = 1
        text_msg = await fetch_quran_ayah(surah, next_ayah)
        surah_name = SURAH_NAMES.get(surah, "")
        msg = (
            f"🌿 *الورد اليومي*\n\n"
            f"📖 سورة *{surah_name}* ({surah}) — آية {next_ayah}/{total_ayahs}\n\n"
            f"{text_msg}" if text_msg else "⚠️ تعذّر تحميل الآية."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ التالية", callback_data=f"wird_next_{surah}_{next_ayah}")],
            [InlineKeyboardButton("🔄 إعادة من البداية", callback_data="wird_restart")],
            [back_btn("main_menu")],
        ])
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

    elif txt in ["📿 التسبيح"]:
        phrase_idx, counter = get_tasbih_session(uid)
        await update.message.reply_text(
            "📿 *التسبيح*\n\nاختر ذكراً للتسبيح:",
            parse_mode=ParseMode.MARKDOWN, reply_markup=build_tasbih_list_keyboard())

    elif txt in ["🌅 أذكار الصباح"]:
        idx = get_adhkar_progress(uid, "morning")
        class FakeQuery:
            def __init__(self, msg): self.message = msg
        await show_adhkar_item(FakeQuery(update.message), "morning", MORNING_ADHKAR, idx, 0)

    elif txt in ["🌆 أذكار المساء"]:
        idx = get_adhkar_progress(uid, "evening")
        class FakeQuery:
            def __init__(self, msg): self.message = msg
        await show_adhkar_item(FakeQuery(update.message), "evening", EVENING_ADHKAR, idx, 0)

    elif txt in ["🌙 أذكار النوم"]:
        idx = get_adhkar_progress(uid, "sleep")
        class FakeQuery:
            def __init__(self, msg): self.message = msg
        await show_adhkar_item(FakeQuery(update.message), "sleep", SLEEP_ADHKAR, idx, 0)

    elif txt in ["✨ أذكار الاستيقاظ"]:   # ← تم التغيير هنا
        idx = get_adhkar_progress(uid, "wakeup")
        class FakeQuery:
            def __init__(self, msg): self.message = msg
        await show_adhkar_item(FakeQuery(update.message), "wakeup", WAKEUP_ADHKAR, idx, 0)

    elif txt in ["🕌 أذكار الصلاة"]:
        await update.message.reply_text(
            "🕌 *أذكار الصلاة*\n\nاختر:",
            parse_mode=ParseMode.MARKDOWN, reply_markup=build_prayer_adhkar_keyboard())

    elif txt in ["🌺 أدعية خاصة"]:
        await update.message.reply_text(
            "🌺 *أدعية خاصة*\n\nاختر الدعاء:",
            parse_mode=ParseMode.MARKDOWN, reply_markup=build_special_duas_keyboard())

    elif txt in ["🌸 أحكام المرأة"]:
        await update.message.reply_text(
            "🌸 *أحكام المرأة*\n\nاختر الدعاء:",
            parse_mode=ParseMode.MARKDOWN, reply_markup=build_woman_adhkar_keyboard())

    elif txt in ["⭐ سنن يوم الجمعة"]:
        await update.message.reply_text(
            "⭐ *سنن يوم الجمعة*\n\nاختر:",
            parse_mode=ParseMode.MARKDOWN, reply_markup=build_friday_keyboard())

    elif txt in ["💧 أذكار الوضوء"]:
        idx = get_adhkar_progress(uid, "wudu")
        class FakeQuery:
            def __init__(self, msg): self.message = msg
        await show_adhkar_item(FakeQuery(update.message), "wudu", WUDU_ADHKAR, idx, 0)

    elif txt in ["🕐 أوقات الصلاة"]:
        city = get_user_city(uid)
        if city:
            msg = await fetch_prayer_times(city)
            kb  = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تغيير المدينة", callback_data="change_city")],
                [back_btn("main_menu")],
            ])
            await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        else:
            await update.message.reply_text(
                "🕐 *أوقات الصلاة*\n\nاختر مدينتك:",
                parse_mode=ParseMode.MARKDOWN, reply_markup=build_city_keyboard())

    elif txt in ["📅 التاريخ اليوم"]:
        msg = await fetch_dates()
        await update.message.reply_text(f"📅 {msg}", parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(uid))

    elif txt in ["📚 حديث اليوم"]:
        row = get_random_hadith()
        if row:
            await update.message.reply_text(
                f"📚 *حديث اليوم*\n\n{row[0]}\n\n📌 _{row[1]}_",
                parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(uid))
        else:
            await update.message.reply_text("⚠️ لا توجد أحاديث بعد.", reply_markup=get_main_keyboard(uid))

    elif txt in ["🤲 دعاء اليوم"]:
        row = get_random_dua()
        if row:
            await update.message.reply_text(
                f"🤲 *دعاء اليوم*\n\n{row[0]}\n\n📌 _{row[1]}_",
                parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(uid))
        else:
            await update.message.reply_text("⚠️ لا توجد أدعية بعد.", reply_markup=get_main_keyboard(uid))

    elif txt in ["🎓 الدورات المجانية"]:
        courses = (
            "🎓 *الدورات الإسلامية المجانية*\n\n"
            "• [أكاديمية إسلام هاوس](https://www.islamhouse.com)\n"
            "• [موقع الدرر السنية](https://dorar.net)\n"
            "• [موقع الإسلام سؤال وجواب](https://islamqa.info/ar)\n"
            "• [موقع طريق الإسلام](https://ar.islamway.net)\n\n"
            "_بارك الله فيك وأعانك على طلب العلم_ 🌿"
        )
        await update.message.reply_text(courses, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(uid))

    elif txt in ["📊 إحصائياتي"]:
        stats = get_user_full_stats(uid)
        surah_name = SURAH_NAMES.get(stats["wird_surah"], "")
        msg = (
            f"📊 *إحصائياتك*\n\n"
            f"🌿 الورد: سورة *{surah_name}* — آية {stats['wird_ayah']}\n"
            f"📿 إجمالي التسبيح: {stats['total_t']}\n"
            f"📖 السور المكتملة: {stats['surahs_done']}\n"
            f"💬 استفساراتك: {stats['inquiries']}\n"
        )
        if stats["tasbih"]:
            msg += "\n*أكثر التسابيح:*\n"
            for phrase, total in stats["tasbih"]:
                msg += f"  • {phrase}: {total}\n"
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(uid))

    elif txt in ["💬 استفسار"]:
        context.user_data["awaiting"] = "inquiry"
        await update.message.reply_text(
            "💬 *استفسار*\n\nاكتب استفسارك وسيصل إلى الإدارة مباشرةً.\n\n"
            "اضغط /cancel للإلغاء أو أرسل استفسارك الآن:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ReplyKeyboardMarkup([["❌ إلغاء"]], resize_keyboard=True))

    elif txt in ["❌ إلغاء"]:
        context.user_data.pop("awaiting", None)
        await update.message.reply_text(
            "✅ تم الإلغاء.", reply_markup=get_main_keyboard(uid))

    elif txt in ["ℹ️ المساعدة"]:
        await cmd_help(update, context)

    elif txt in ["⚙️ لوحة الإدارة"]:
        if not is_admin(uid):
            await update.message.reply_text("⚠️ ليس لديك صلاحية.", reply_markup=get_main_keyboard(uid)); return
        stats = get_admin_stats()
        msg = (
            f"⚙️ *لوحة الإدارة*\n\n"
            f"👥 المستخدمون: {stats['users']} | 🚫 محظورون: {stats['banned']}\n"
            f"🟢 نشطون اليوم: {stats['active_today']} | 👤 مشرفون: {stats['admins']}\n"
            f"📚 أحاديث: {stats['hadiths']} | 🤲 أدعية: {stats['duas']}\n"
            f"📝 محتوى: {stats['content']} | 📿 تسبيح: {stats['tasbih_total']}\n"
            f"💬 معلق: {stats['pending']} | ✅ مُجاب: {stats['replied']}"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=build_admin_keyboard())

    else:
        await update.message.reply_text(
            "🌿 اختر من القائمة أدناه:", reply_markup=get_main_keyboard(uid))

# ══════════════════════════════════════════════════════════════════
# Handler — Callback Queries
# ══════════════════════════════════════════════════════════════════
@banned_check
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid  = query.from_user.id
    data = query.data

    # ── رجوع للقائمة الرئيسية ────────────────────────────────────
    if data == "main_menu":
        await query.message.reply_text("🌿 القائمة الرئيسية:", reply_markup=get_main_keyboard(uid))
        try: await query.message.delete()
        except: pass
        return

    # ── القرآن — اختيار الرواية ──────────────────────────────────
    if data == "quran_back":
        await safe_edit(query, "📖 *القرآن الكريم*\n\nاختر رواية القراءة:", reply_markup=build_quran_keyboard())
        return

    if data == "quran_random":
        s = random.randint(1, 114)
        a = random.randint(1, SURAH_AYAH_COUNT[s])
        txt = await fetch_quran_ayah(s, a)
        msg = (
            f"🎲 *آية عشوائية*\n\n"
            f"📖 سورة *{SURAH_NAMES[s]}* — آية {a}\n\n"
            f"{txt}" if txt else "⚠️ تعذّر تحميل الآية."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 آية أخرى", callback_data="quran_random")],
            [back_btn("quran_back")],
        ])
        await safe_edit(query, msg, reply_markup=kb)
        return

    # ── القرآن — قائمة السور (صفحات) ────────────────────────────
    if data.startswith("sp_"):
        parts  = data.split("_")
        page   = int(parts[1])
        riwaya = parts[2]
        riwaya_name = "حفص عن عاصم" if riwaya == "hafs" else "ورش عن نافع"
        await safe_edit(
            query,
            f"📖 *رواية {riwaya_name}*\n\nاختر السورة:",
            reply_markup=build_surah_keyboard(page, riwaya))
        return

    # ── القرآن — اختيار سورة → خيارات البداية ───────────────────
    if data.startswith("ss_"):
        parts  = data.split("_")
        surah  = int(parts[1])
        riwaya = parts[2]
        surah_name = SURAH_NAMES.get(surah, "")
        total  = SURAH_AYAH_COUNT.get(surah, 1)
        last   = get_surah_progress(uid, surah, riwaya)
        riwaya_name = "حفص" if riwaya == "hafs" else "ورش"
        msg = (
            f"📖 *سورة {surah_name}*\n"
            f"رواية: {riwaya_name} | عدد الآيات: {total}\n\n"
            f"من أين تريد البدء؟"
        )
        await safe_edit(query, msg, reply_markup=build_surah_start_keyboard(uid, surah, riwaya))
        return

    # ── القرآن — اختيار آية معينة (صفحات الأرقام) ───────────────
    if data.startswith("choose_ayah_"):
        parts  = data.split("_")
        surah  = int(parts[2])
        riwaya = parts[3]
        surah_name = SURAH_NAMES.get(surah, "")
        await safe_edit(
            query,
            f"🔢 *سورة {surah_name}* — اختر رقم الآية:",
            reply_markup=build_ayah_choice_keyboard(surah, riwaya, 0))
        return

    if data.startswith("ayah_page_"):
        parts  = data.split("_")
        surah  = int(parts[2])
        riwaya = parts[3]
        page   = int(parts[4])
        surah_name = SURAH_NAMES.get(surah, "")
        await safe_edit(
            query,
            f"🔢 *سورة {surah_name}* — اختر رقم الآية:",
            reply_markup=build_ayah_choice_keyboard(surah, riwaya, page))
        return

    # ── القرآن — قراءة آية ───────────────────────────────────────
    if data.startswith("read_"):
        parts  = data.split("_")
        surah  = int(parts[1])
        ayah   = int(parts[2])
        riwaya = parts[3]
        total  = SURAH_AYAH_COUNT[surah]
        if ayah > total:
            save_surah_progress(uid, surah, total, riwaya)
            msg = f"📖 سورة *{SURAH_NAMES[surah]}* — ✅ أتممت قراءة السورة!"
            kb  = InlineKeyboardMarkup([
                [InlineKeyboardButton("📖 سورة أخرى", callback_data=f"sp_0_{riwaya}")],
                [back_btn("main_menu")],
            ])
            await safe_edit(query, msg, reply_markup=kb)
            return
        txt_ayah = await fetch_quran_ayah(surah, ayah, riwaya)
        riwaya_name = "حفص" if riwaya == "hafs" else "ورش"
        msg = (
            f"📖 *سورة {SURAH_NAMES[surah]}* — رواية {riwaya_name}\n"
            f"آية {ayah}/{total}\n\n"
            f"{txt_ayah}" if txt_ayah else "⚠️ تعذّر تحميل الآية."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ التالية", callback_data=f"read_{surah}_{ayah+1}_{riwaya}")],
            [InlineKeyboardButton("💾 حفظ وخروج", callback_data=f"save_surah_{surah}_{ayah}_{riwaya}")],
            [back_btn(f"ss_{surah}_{riwaya}")],
        ])
        await safe_edit(query, msg, reply_markup=kb)
        return

    if data.startswith("save_surah_"):
        parts  = data.split("_")
        surah  = int(parts[2])
        ayah   = int(parts[3])
        riwaya = parts[4]
        save_surah_progress(uid, surah, ayah, riwaya)
        await query.answer(f"✅ تم حفظ تقدمك عند آية {ayah}", show_alert=True)
        return

    # ── الورد اليومي ─────────────────────────────────────────────
    if data.startswith("wird_next_"):
        parts = data.split("_")
        surah = int(parts[2]); ayah = int(parts[3])
        save_wird_progress(uid, surah, ayah)
        total2 = SURAH_AYAH_COUNT.get(surah, 286)
        nexta  = ayah + 1
        if nexta > total2:
            surah += 1; nexta = 1
            if surah > 114: surah = 1
        txt_ayah   = await fetch_quran_ayah(surah, nexta)
        surah_name = SURAH_NAMES.get(surah, "")
        msg = (
            f"🌿 *الورد اليومي*\n\n"
            f"📖 سورة *{surah_name}* ({surah}) — آية {nexta}/{total2}\n\n"
            f"{txt_ayah}" if txt_ayah else "⚠️ تعذّر تحميل الآية."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ التالية", callback_data=f"wird_next_{surah}_{nexta}")],
            [InlineKeyboardButton("🔄 إعادة من البداية", callback_data="wird_restart")],
            [back_btn("main_menu")],
        ])
        await safe_edit(query, msg, reply_markup=kb)
        return

    if data == "wird_restart":
        save_wird_progress(uid, 2, 0)
        await query.answer("✅ تم إعادة الورد من البداية", show_alert=True)
        txt_ayah = await fetch_quran_ayah(2, 1)
        msg = (
            f"🌿 *الورد اليومي — من البداية*\n\n"
            f"📖 سورة *البقرة* (2) — آية 1/{SURAH_AYAH_COUNT[2]}\n\n"
            f"{txt_ayah}" if txt_ayah else "⚠️ تعذّر تحميل الآية."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ التالية", callback_data="wird_next_2_1")],
            [InlineKeyboardButton("🔄 إعادة من البداية", callback_data="wird_restart")],
            [back_btn("main_menu")],
        ])
        await safe_edit(query, msg, reply_markup=kb)
        return

    # ── التسبيح ──────────────────────────────────────────────────
    if data == "tasbih_list":
        await safe_edit(query, "📿 *التسبيح*\n\nاختر ذكراً:", reply_markup=build_tasbih_list_keyboard())
        return

    if data.startswith("tsb_start_"):
        phrase_idx = int(data.split("_")[2])
        phrase, fad, req = TASBIH_LIST[phrase_idx]
        saved_idx, saved_counter = get_tasbih_session(uid)
        counter = saved_counter if saved_idx == phrase_idx else 0
        save_tasbih_session(uid, phrase_idx, counter)
        msg = (
            f"📿 *{phrase}*\n\n"
            f"_{fad}_\n\n"
            f"العدد المطلوب: {req}\n"
            f"تقدمك الحالي: {counter}/{req}"
        )
        await safe_edit(query, msg, reply_markup=build_tasbih_counter_keyboard(phrase_idx, counter, req))
        return

    if data.startswith("tsb_count_"):
        parts      = data.split("_")
        phrase_idx = int(parts[2]); counter = int(parts[3]) + 1
        phrase, fad, req = TASBIH_LIST[phrase_idx]
        save_tasbih_session(uid, phrase_idx, counter)
        if counter >= req:
            log_tasbih(uid, phrase, counter)
            motivation = random.choice(MOTIVATION_MSGS)
            msg = f"📿 *{phrase}*\n\n✅ أتممت {req} مرة!\n\n{motivation}"
        else:
            msg = (
                f"📿 *{phrase}*\n\n"
                f"_{fad}_\n\n"
                f"العدد المطلوب: {req}\n"
                f"تقدمك الحالي: {counter}/{req}"
            )
        await safe_edit(query, msg, reply_markup=build_tasbih_counter_keyboard(phrase_idx, counter, req))
        return

    if data.startswith("tsb_save_"):
        parts = data.split("_"); phrase_idx = int(parts[2]); counter = int(parts[3])
        save_tasbih_session(uid, phrase_idx, counter)
        log_tasbih(uid, TASBIH_LIST[phrase_idx][0], counter)
        await query.answer(f"✅ تم حفظ {counter} تسبيحة", show_alert=True)
        return

    if data.startswith("tsb_reset_"):
        phrase_idx = int(data.split("_")[2])
        reset_tasbih_session(uid); save_tasbih_session(uid, phrase_idx, 0)
        phrase, fad, req = TASBIH_LIST[phrase_idx]
        msg = f"📿 *{phrase}*\n\n_{fad}_\n\nالعدد المطلوب: {req}\nتقدمك الحالي: 0/{req}"
        await safe_edit(query, msg, reply_markup=build_tasbih_counter_keyboard(phrase_idx, 0, req))
        return

    if data.startswith("tsb_done_"):
        phrase_idx = int(data.split("_")[2])
        phrase, fad, req = TASBIH_LIST[phrase_idx]
        log_tasbih(uid, phrase, req); reset_tasbih_session(uid)
        motivation = random.choice(MOTIVATION_MSGS)
        msg = f"📿 *{phrase}*\n\n✅ أتممت {req} مرة!\n\n{motivation}"
        await safe_edit(query, msg, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 قائمة التسابيح", callback_data="tasbih_list")],
            [back_btn("main_menu")],
        ]))
        return

    # ── الأذكار ───────────────────────────────────────────────────
    if data.startswith("adhkar_next_"):
        parts = data.split("_"); key = parts[2]; idx = int(parts[3]); counter = int(parts[4])
        if key in ADHKAR_MAP:
            _, lst = ADHKAR_MAP[key]
            save_adhkar_progress(uid, key, idx)
            await show_adhkar_item(query, key, lst, idx, counter)
        return

    if data.startswith("adhkar_count_"):
        parts = data.split("_"); key = parts[2]; idx = int(parts[3]); counter = int(parts[4])
        if key in ADHKAR_MAP:
            _, lst = ADHKAR_MAP[key]
            item_text, item_src, item_req = lst[idx]
            if counter >= item_req:
                next_idx = idx + 1
                if next_idx >= len(lst):
                    reset_adhkar_progress(uid, key)
                    motivation = random.choice(MOTIVATION_MSGS)
                    title = ADHKAR_MAP[key][0]
                    await safe_edit(query,
                        f"✅ *أتممت {title}!*\n\n{motivation}",
                        reply_markup=InlineKeyboardMarkup([[back_btn("main_menu")]]))
                    return
                save_adhkar_progress(uid, key, next_idx)
                await show_adhkar_item(query, key, lst, next_idx, 0)
            else:
                await show_adhkar_item(query, key, lst, idx, counter)
        return

    if data.startswith("adhkar_save_"):
        parts = data.split("_"); key = parts[2]; idx = int(parts[3])
        save_adhkar_progress(uid, key, idx)
        await query.answer("✅ تم حفظ التقدم", show_alert=True)
        return

    if data.startswith("adhkar_restart_"):
        key = data.split("_")[2]
        reset_adhkar_progress(uid, key)
        if key in ADHKAR_MAP:
            _, lst = ADHKAR_MAP[key]
            await show_adhkar_item(query, key, lst, 0, 0)
        return

    if data.startswith("adhkar_done_"):
        key = data.split("_")[2]
        reset_adhkar_progress(uid, key)
        motivation = random.choice(MOTIVATION_MSGS)
        label = ADHKAR_MAP[key][0] if key in ADHKAR_MAP else "الأذكار"
        await safe_edit(query,
            f"✅ *أتممت {label}!*\n\n{motivation}",
            reply_markup=InlineKeyboardMarkup([[back_btn("main_menu")]]))
        return

    # ── أذكار الصلاة ──────────────────────────────────────────────
    if data.startswith("pr_adhkar_"):
        key = data[len("pr_adhkar_"):]
        if key in PRAYER_ADHKAR:
            lst  = PRAYER_ADHKAR[key]
            item = lst[0]
            text = f"🕌 *{key}*\n\n{item[0]}\n\n📌 _{item[1]}_"
            if len(lst) > 1:
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("▶️ التالي", callback_data=f"pr_next_{key}_1")],
                    [back_btn("prayer_adhkar_menu")],
                ])
            else:
                kb = InlineKeyboardMarkup([[back_btn("prayer_adhkar_menu")]])
            await safe_edit(query, text, reply_markup=kb)
        return

    if data == "prayer_adhkar_menu":
        await safe_edit(query, "🕌 *أذكار الصلاة*\n\nاختر:", reply_markup=build_prayer_adhkar_keyboard())
        return

    if data.startswith("pr_next_"):
        parts = data.split("_", 3); key = parts[2]; idx = int(parts[3])
        if key in PRAYER_ADHKAR:
            lst = PRAYER_ADHKAR[key]
            if idx >= len(lst):
                await safe_edit(query, f"✅ *{key}* — تم!", reply_markup=InlineKeyboardMarkup([[back_btn("prayer_adhkar_menu")]]))
                return
            item = lst[idx]
            text = f"🕌 *{key}* ({idx+1}/{len(lst)})\n\n{item[0]}\n\n📌 _{item[1]}_"
            nav  = []
            if idx + 1 < len(lst):
                nav.append(InlineKeyboardButton("▶️ التالي", callback_data=f"pr_next_{key}_{idx+1}"))
            else:
                nav.append(InlineKeyboardButton("✅ تم", callback_data="prayer_adhkar_menu"))
            kb = InlineKeyboardMarkup([nav, [back_btn("prayer_adhkar_menu")]])
            await safe_edit(query, text, reply_markup=kb)
        return

    # ── الأدعية الخاصة ────────────────────────────────────────────
    if data.startswith("sdua_"):
        idx  = int(data.split("_")[1])
        keys = list(SPECIAL_DUAS.keys())
        if idx < len(keys):
            key   = keys[idx]
            items = SPECIAL_DUAS[key]
            text  = f"🤲 *{key}*\n\n"
            for item in items:
                text += f"{item[0]}\n\n📌 _{item[1]}_\n\n"
            kb = InlineKeyboardMarkup([[back_btn("special_duas_menu")]])
            await safe_edit(query, text.strip(), reply_markup=kb)
        return

    if data == "special_duas_menu":
        await safe_edit(query, "🌺 *أدعية خاصة*\n\nاختر:", reply_markup=build_special_duas_keyboard())
        return

    # ── أحكام المرأة ──────────────────────────────────────────────
    if data.startswith("wad_"):
        idx  = int(data.split("_")[1])
        keys = list(WOMAN_ADHKAR.keys())
        if idx < len(keys):
            key   = keys[idx]
            items = WOMAN_ADHKAR[key]
            text  = f"🌸 *{key}*\n\n"
            for item in items:
                text += f"{item[0]}\n\n📌 _{item[1]}_\n\n"
            kb = InlineKeyboardMarkup([[back_btn("woman_adhkar_menu")]])
            await safe_edit(query, text.strip(), reply_markup=kb)
        return

    if data == "woman_adhkar_menu":
        await safe_edit(query, "🌸 *أحكام المرأة*\n\nاختر:", reply_markup=build_woman_adhkar_keyboard())
        return

    # ── المدن — أوقات الصلاة ─────────────────────────────────────
    if data.startswith("city_"):
        city = data[5:]
        save_user_city(uid, city)
        msg = await fetch_prayer_times(city)
        kb  = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 تغيير المدينة", callback_data="change_city")],
            [back_btn("main_menu")],
        ])
        await safe_edit(query, msg, reply_markup=kb)
        return

    if data == "change_city":
        await safe_edit(query, "🕐 *أوقات الصلاة*\n\nاختر مدينتك:", reply_markup=build_city_keyboard())
        return

    # ── سنن الجمعة ────────────────────────────────────────────────
    if data.startswith("friday_surah_"):
        surah_num  = int(data.split("_")[2])
        desc       = FRIDAY_SURAHS.get(surah_num, "")
        txt_ayah   = await fetch_quran_ayah(surah_num, 1)
        msg = (
            f"📖 *{desc}*\n\n"
            f"سورة *{SURAH_NAMES[surah_num]}* — الآية الأولى:\n\n"
            f"{txt_ayah}" if txt_ayah else "⚠️ تعذّر تحميل الآية."
        )
        await safe_edit(query, msg, reply_markup=InlineKeyboardMarkup([[back_btn("friday_menu")]]))
        return

    if data.startswith("friday_info_"):
        idx = int(data.split("_")[2])
        if idx < len(FRIDAY_SUNNAN):
            s   = FRIDAY_SUNNAN[idx]
            msg = f"⭐ *{s['title']}*\n\n{s['text']}\n\n📌 _{s['source']}_"
            await safe_edit(query, msg, reply_markup=InlineKeyboardMarkup([[back_btn("friday_menu")]]))
        return

    if data == "friday_menu":
        await safe_edit(query, "⭐ *سنن يوم الجمعة*\n\nاختر:", reply_markup=build_friday_keyboard())
        return

    # ── الإدارة ───────────────────────────────────────────────────
    if data == "adm_inquiries":
        rows = get_pending_inquiries()
        if not rows:
            await safe_edit(query, "✅ لا توجد استفسارات معلقة.", reply_markup=InlineKeyboardMarkup([[back_btn("adm_back")]]))
            return
        btns = []
        text = "📋 *الاستفسارات المعلقة:*\n\n"
        for r in rows[:10]:
            iid, uid2, uname, fname, msg_txt, created = r
            text += f"#{iid} — {fname} (@{uname})\n{msg_txt[:80]}...\n\n"
            btns.append([InlineKeyboardButton(f"↩️ رد على #{iid}", callback_data=f"adm_reply_{iid}")])
        btns.append([back_btn("adm_back")])
        await safe_edit(query, text, reply_markup=InlineKeyboardMarkup(btns))
        return

    if data == "adm_all_inquiries":
        rows = get_all_inquiries()
        if not rows:
            await safe_edit(query, "⚠️ لا توجد استفسارات.", reply_markup=InlineKeyboardMarkup([[back_btn("adm_back")]]))
            return
        text = "📜 *كل الاستفسارات:*\n\n"
        for r in rows[:10]:
            iid, uid2, uname, fname, msg_txt, status, created = r
            icon = "✅" if status == "replied" else "⏳"
            text += f"{icon} #{iid} — {fname} | {msg_txt[:60]}...\n"
        await safe_edit(query, text, reply_markup=InlineKeyboardMarkup([[back_btn("adm_back")]]))
        return

    if data.startswith("adm_reply_"):
        iid = int(data.split("_")[2])
        context.user_data["awaiting"] = "adm_reply"
        context.user_data["reply_iid"] = iid
        await safe_edit(query, f"↩️ اكتب ردك على الاستفسار #{iid}:")
        return

    if data == "adm_users_list":
        rows = get_users_list()
        text = "👥 *قائمة المستخدمين (آخر 30):*\n\n"
        for r in rows:
            uid2, uname, fname, adm, banned, seen = r
            icon = "🚫" if banned else ("👤" if adm else "✅")
            text += f"{icon} {fname} (@{uname}) — {uid2}\n"
        await safe_edit(query, text, reply_markup=InlineKeyboardMarkup([[back_btn("adm_back")]]))
        return

    if data == "adm_stats":
        stats = get_admin_stats()
        msg = (
            f"📊 *إحصائيات البوت*\n\n"
            f"👥 المستخدمون: {stats['users']} | 🚫 محظورون: {stats['banned']}\n"
            f"🟢 نشطون اليوم: {stats['active_today']} | 👤 مشرفون: {stats['admins']}\n"
            f"📚 أحاديث: {stats['hadiths']} | 🤲 أدعية: {stats['duas']}\n"
            f"📝 محتوى: {stats['content']} | 📿 تسبيح: {stats['tasbih_total']}\n"
            f"💬 معلق: {stats['pending']} | ✅ مُجاب: {stats['replied']}"
        )
        await safe_edit(query, msg, reply_markup=InlineKeyboardMarkup([[back_btn("adm_back")]]))
        return

    if data == "adm_back":
        stats = get_admin_stats()
        msg = (
            f"⚙️ *لوحة الإدارة*\n\n"
            f"👥 المستخدمون: {stats['users']} | 🚫 محظورون: {stats['banned']}\n"
            f"🟢 نشطون اليوم: {stats['active_today']}"
        )
        await safe_edit(query, msg, reply_markup=build_admin_keyboard())
        return

    prompts = {
        "adm_add_hadith":  "📚 أرسل: نص الحديث | المصدر",
        "adm_add_dua":     "🤲 أرسل: نص الدعاء | المصدر",
        "adm_del_hadith":  "🗑 أرسل رقم الحديث للحذف:",
        "adm_del_dua":     "🗑 أرسل رقم الدعاء للحذف:",
        "adm_add_content": "📝 أرسل: التصنيف | النص | المصدر",
        "adm_del_content": "🗑 أرسل رقم المحتوى للحذف:",
        "adm_add_admin":   "👤 أرسل ID المستخدم لتعيينه مشرفاً:",
        "adm_del_admin":   "❌ أرسل ID المشرف لإزالة صلاحيته:",
        "adm_ban":         "🚫 أرسل ID المستخدم لحظره:",
        "adm_unban":       "✅ أرسل ID المستخدم لرفع حظره:",
        "adm_send_user":   "📩 أرسل الرسالة التي تريد إرسالها:",
        "adm_broadcast":   "📢 أرسل رسالة البث العام:",
    }
    if data in prompts:
        context.user_data["awaiting"] = data[4:]  # remove "adm_"
        await safe_edit(query, prompts[data])
        return

# ══════════════════════════════════════════════════════════════════
# الإشعارات اليومية
# ══════════════════════════════════════════════════════════════════
async def daily_notifications(app):
    while True:
        try:
            now = datetime.now()
            if now.hour == 6 and now.minute == 0:
                users = get_all_users()
                for uid in users:
                    if not notif_already_sent(uid, "morning"):
                        try:
                            await app.bot.send_message(
                                uid,
                                "🌅 *صباح الخير!*\n\nلا تنس أذكار الصباح 🌿\n\nاضغط على *أذكار الصباح* من القائمة.",
                                parse_mode=ParseMode.MARKDOWN)
                            mark_notif_sent(uid, "morning")
                        except: pass

            if now.hour == 18 and now.minute == 0:
                users = get_all_users()
                for uid in users:
                    if not notif_already_sent(uid, "evening"):
                        try:
                            await app.bot.send_message(
                                uid,
                                "🌆 *مساء الخير!*\n\nلا تنس أذكار المساء 🌿\n\nاضغط على *أذكار المساء* من القائمة.",
                                parse_mode=ParseMode.MARKDOWN)
                            mark_notif_sent(uid, "evening")
                        except: pass

        except Exception as e:
            logger.error(f"Notification error: {e}")
        await asyncio.sleep(60)

# ══════════════════════════════════════════════════════════════════
# main
# ══════════════════════════════════════════════════════════════════
async def post_init(app):
    asyncio.create_task(daily_notifications(app))

def main():
    init_db()
    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🕌 بوت المسلم يعمل الآن...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
