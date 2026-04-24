from datetime import datetime

from .extensions import db


PEDAGOGICAL_COURSE_SPECS = [
    {
        "level": "A1",
        "name": "Parcours Arabe A1 - Bases utiles",
        "description": (
            "Un parcours debutant pour saluer, se presenter, comprendre les mots utiles du quotidien "
            "et construire des phrases tres simples avec confiance."
        ),
        "image_url": "uploads/courses/cours_5_yeshi-kangrang-PM_VwL2ypes-unsplash.jpg",
        "pdf_url": "uploads/pdfs/support_salutations.pdf",
        "legacy_image_urls": ["uploads/courses/course_demo_salutations.svg"],
    },
    {
        "level": "A2",
        "name": "Parcours Arabe A2 - Quotidien actif",
        "description": (
            "Un parcours elementaire pour agir au quotidien: achats, deplacements, travail, sante, "
            "demarches et conversations simples en arabe."
        ),
        "image_url": "uploads/courses/cours_6_DITP2945.PNG",
        "pdf_url": "uploads/pdfs/lecon_6_Support_de_cours_-_SCM_toutes_les_sAances.pdf",
        "legacy_image_urls": ["uploads/courses/course_demo_quotidien.svg"],
    },
]

PEDAGOGICAL_COURSE_NAMES = tuple(spec["name"] for spec in PEDAGOGICAL_COURSE_SPECS)
PEDAGOGICAL_LEGACY_COURSE_NAMES = (
    "Démo A1 - Salutations et alphabet",
    "Démo A2 - Vocabulaire du quotidien",
)
PEDAGOGICAL_LEGACY_COURSE_IMAGE_URLS = tuple(
    legacy_image_url
    for course_spec in PEDAGOGICAL_COURSE_SPECS
    for legacy_image_url in course_spec.get("legacy_image_urls", [])
)

_ARABIC_TO_LATIN = {
    "ا": "a",
    "أ": "a",
    "إ": "i",
    "آ": "a",
    "ب": "b",
    "ت": "t",
    "ث": "th",
    "ج": "j",
    "ح": "h",
    "خ": "kh",
    "د": "d",
    "ذ": "dh",
    "ر": "r",
    "ز": "z",
    "س": "s",
    "ش": "sh",
    "ص": "s",
    "ض": "d",
    "ط": "t",
    "ظ": "z",
    "ع": "a",
    "غ": "gh",
    "ف": "f",
    "ق": "q",
    "ك": "k",
    "ل": "l",
    "م": "m",
    "ن": "n",
    "ه": "h",
    "و": "w",
    "ؤ": "w",
    "ي": "y",
    "ئ": "y",
    "ى": "a",
    "ة": "a",
    "ء": "'",
    " ": " ",
    "؟": "?",
}

_THEME_TEMPLATES = {
    "Salutations": "نستعمل {term} في البداية.",
    "Classe": "اتعلم {term} في الصف.",
    "Temps": "استعمل {term} كل يوم.",
    "Maison": "ارى {term} في البيت.",
    "Cuisine": "احب {term} كثيرا.",
    "Ville": "استعمل {term} في الطريق.",
    "Routine": "استعمل {term} في يومي.",
    "Corps": "اتعلم {term} في هذا الدرس.",
    "Vetements": "اختار {term} اليوم.",
    "Loisirs": "احب {term} في وقت الفراغ.",
    "Achats": "احتاج {term} عند الشراء.",
    "Voyage": "استعمل {term} في السفر.",
    "Travail": "استعمل {term} في العمل.",
    "Demarches": "احتاج {term} في الادارة.",
    "Numerique": "استعمل {term} على الهاتف.",
    "Sentiments": "نستعمل {term} في الحوار.",
    "Sante": "اسمع {term} عند الطبيب.",
    "Habitat": "استعمل {term} في البيت.",
    "Relations": "نستعمل {term} مع الاصدقاء.",
    "Opinions": "استعمل {term} في النقاش.",
}


def _parse_entries(raw_entries):
    entries = []
    for raw_line in raw_entries.strip().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        arabic, french = [chunk.strip() for chunk in line.split("|", 1)]
        entries.append({"mot_arabe": arabic, "traduction_fr": french})
    return entries


def _course_name_for_level(level):
    for course_spec in PEDAGOGICAL_COURSE_SPECS:
        if course_spec["level"] == level:
            return course_spec["name"]
    raise ValueError(f"Niveau inconnu: {level}")


def _lesson(level, order, title, theme, goal, model_sentence, raw_entries):
    return {
        "level": level,
        "course_name": _course_name_for_level(level),
        "order": order,
        "title": title,
        "theme": theme,
        "goal": goal,
        "model_sentence": model_sentence,
        "entries": _parse_entries(raw_entries),
    }


PEDAGOGICAL_LESSON_SPECS = [
    _lesson(
        "A1",
        1,
        "Saluer et etre poli",
        "Salutations",
        "Apprendre les salutations, les reponses courtes et les consignes les plus frequentes.",
        "صباح الخير يا صديقي",
        """
        مرحبا|bonjour
        اهلا|salut
        اهلا وسهلا|bienvenue
        صباح الخير|bonjour du matin
        مساء الخير|bonsoir
        تصبح على خير|bonne nuit
        مع السلامة|au revoir
        الى اللقاء|a bientot
        سلام|paix / salut
        شكرا|merci
        شكرا جزيلا|merci beaucoup
        عفوا|de rien
        من فضلك|s'il vous plait
        نعم|oui
        لا|non
        ربما|peut-etre
        بخير|bien
        كيف حالك؟|comment ca va ?
        انا بخير|je vais bien
        ما اسمك؟|comment t'appelles-tu ?
        اسمي|je m'appelle
        تشرفنا|enchante
        آسف|desole
        لا باس|ce n'est pas grave
        تفضل|vas-y / prends
        انتظر|attends
        هيا|allons-y
        هنا|ici
        هناك|la-bas
        الآن|maintenant
        دائما|toujours
        كثيرا|beaucoup
        قليلا|un peu
        مرة اخرى|encore une fois
        جيد جدا|tres bien
        ممتاز|excellent
        سهل|facile
        صعب|difficile
        واضح|clair
        ببطء|lentement
        بسرعة|rapidement
        اسمع|ecoute
        كرر|repete
        اقرأ|lis
        اكتب|ecris
        افهم|je comprends
        لا افهم|je ne comprends pas
        ممكن|possible
        جاهز|pret
        متاكد|sur
        """,
    ),
    _lesson(
        "A1",
        2,
        "Se presenter et parler de la classe",
        "Classe",
        "Nommer les personnes, les pronoms et les objets les plus utiles de la classe.",
        "انا طالب جديد في الصف",
        """
        أنا|je / moi
        انت|tu
        انتِ|tu (feminin)
        هو|il
        هي|elle
        نحن|nous
        هذا|ceci
        هذه|celle-ci
        ذلك|cela
        تلك|celle-la
        من|qui
        ماذا|quoi
        اين|ou
        طالب|etudiant
        طالبة|etudiante
        معلم|enseignant
        معلمة|enseignante
        تلميذ|eleve
        تلميذة|eleve (feminin)
        مدرسة|ecole
        فصل|classe
        كتاب|livre
        دفتر|cahier
        قلم|stylo
        حقيبة|sac
        كرسي|chaise
        طاولة|table
        سبورة|tableau
        باب|porte
        نافذة|fenetre
        مكتب|bureau
        درس|lecon
        سؤال|question
        جواب|reponse
        لغة|langue
        عربية|arabe
        فرنسية|francais
        اسم|nom
        لقب|surnom
        صديق|ami
        صديقة|amie
        ولد|garcon
        بنت|fille
        جديد|nouveau
        قديم|ancien
        صغير|petit
        كبير|grand
        حاضر|present
        غائب|absent
        مجتهد|applique
        """,
    ),
    _lesson(
        "A1",
        3,
        "Compter et dire le temps",
        "Temps",
        "Compter jusqu'a vingt et comprendre les mots simples du temps et du calendrier.",
        "الدرس الساعة العاشرة صباحا",
        """
        صفر|zero
        واحد|un
        اثنان|deux
        ثلاثة|trois
        اربعة|quatre
        خمسة|cinq
        ستة|six
        سبعة|sept
        ثمانية|huit
        تسعة|neuf
        عشرة|dix
        احد عشر|onze
        اثنا عشر|douze
        ثلاثة عشر|treize
        اربعة عشر|quatorze
        خمسة عشر|quinze
        ستة عشر|seize
        سبعة عشر|dix-sept
        ثمانية عشر|dix-huit
        تسعة عشر|dix-neuf
        عشرون|vingt
        ساعة|heure
        دقيقة|minute
        ثانية|seconde
        يوم|jour
        اسبوع|semaine
        شهر|mois
        سنة|annee
        صباح|matin
        ظهر|midi
        مساء|soir
        ليلة|nuit
        امس|hier
        غدا|demain
        الاثنين|lundi
        الثلاثاء|mardi
        الاربعاء|mercredi
        الخميس|jeudi
        الجمعة|vendredi
        السبت|samedi
        الاحد|dimanche
        متى|quand
        كم|combien
        الاول|premier
        الثاني|deuxieme
        الثالث|troisieme
        الرابع|quatrieme
        الخامس|cinquieme
        الوقت|le temps
        موعد|rendez-vous
        """,
    ),
    _lesson(
        "A1",
        4,
        "La famille et la maison",
        "Maison",
        "Parler des proches, des pieces et des objets simples de la maison.",
        "هذه اسرتي في البيت",
        """
        اب|pere
        ام|mere
        اخ|frere
        اخت|soeur
        جد|grand-pere
        جدة|grand-mere
        عم|oncle paternel
        عمة|tante paternelle
        خال|oncle maternel
        خالة|tante maternelle
        ابن|fils
        ابنة|fille
        زوج|mari
        زوجة|epouse
        عائلة|famille
        بيت|maison
        منزل|domicile
        غرفة|chambre
        مطبخ|cuisine
        حمام|salle de bain
        سرير|lit
        وسادة|oreiller
        بطانية|couverture
        خزانة|armoire
        مفتاح|cle
        ضوء|lumiere
        كهرباء|electricite
        حديقة|jardin
        شرفة|balcon
        جدار|mur
        سقف|plafond
        ارض|sol
        عنوان|adresse
        جار|voisin
        قريب|proche
        بعيد|loin
        اسكن|j'habite
        اسرة|foyer
        طفل|enfant
        اطفال|enfants
        غرفة الجلوس|salon
        غرفة النوم|chambre a coucher
        درج|escalier
        ممر|couloir
        ستارة|rideau
        مكنسة|balai
        مرآة|miroir
        وسخ|sale
        نظيف|propre
        هادئ|calme
        """,
    ),
    _lesson(
        "A1",
        5,
        "Manger et boire simplement",
        "Cuisine",
        "Nommer les aliments, les boissons et le materiel tres frequent de la table.",
        "اشرب الماء مع الخبز",
        """
        ماء|eau
        شاي|the
        قهوة|cafe
        حليب|lait
        عصير|jus
        خبز|pain
        ارز|riz
        لحم|viande
        دجاج|poulet
        سمك|poisson
        بيضة|oeuf
        جبن|fromage
        زبدة|beurre
        سكر|sucre
        ملح|sel
        فلفل|poivre
        تفاح|pomme
        موز|banane
        برتقال|orange
        تمر|datte
        عنب|raisin
        طماطم|tomate
        بطاطا|pomme de terre
        خيار|concombre
        جزر|carotte
        سلطة|salade
        حساء|soupe
        فطور|petit-dejeuner
        غداء|dejeuner
        عشاء|diner
        جائع|affame
        عطشان|assoiffe
        لذيذ|delicieux
        ساخن|chaud
        بارد|froid
        طبق|plat
        ملعقة|cuillere
        شوكة|fourchette
        سكين|couteau
        كوب|tasse
        صحن|assiette
        قدر|marmite
        ثلاجة|refrigerateur
        فاكهة|fruit
        خضار|legumes
        وصفة|recette
        طعام|nourriture
        شراب|boisson
        مائدة|table a manger
        وجبة|repas
        """,
    ),
    _lesson(
        "A1",
        6,
        "Se reperer en ville",
        "Ville",
        "Comprendre les lieux du quartier, les directions simples et les gestes utiles du trajet.",
        "اذهب الى السوق ثم اعود",
        """
        شارع|rue
        طريق|route
        سيارة|voiture
        حافلة|bus
        قطار|train
        دراجة|velo
        محطة|station
        مطار|aeroport
        سيارة اجرة|taxi
        اشارة مرور|feu de circulation
        جسر|pont
        نفق|tunnel
        سوق|marche
        متجر|magasin
        صيدلية|pharmacie
        مستشفى|hopital
        مسجد|mosquee
        حديقة عامة|parc public
        مكتب بريد|bureau de poste
        بنك|banque
        فندق|hotel
        مطعم شعبي|restaurant populaire
        ساحة|place
        حي|quartier
        قرية|village
        خريطة|carte
        يمين|droite
        يسار|gauche
        مستقيم|tout droit
        قريب من|pres de
        بعيد عن|loin de
        امام|devant
        خلف|derriere
        بين|entre
        فوق|au-dessus
        تحت|sous
        داخل|a l'interieur
        خارج|a l'exterieur
        ادخل|entre
        اخرج|sors
        امشي|je marche
        اقف|je m'arrete
        انعطف|tourne
        توقف|arrete-toi
        مدخل|entree
        مخرج|sortie
        رصيف|trottoir
        دوار|rond-point
        تقاطع|carrefour
        رحلة قصيرة|petit trajet
        """,
    ),
    _lesson(
        "A1",
        7,
        "Les actions du quotidien",
        "Routine",
        "Parler des actions les plus simples de la journee et des habitudes courtes.",
        "استيقظ مبكرا ثم ادرس",
        """
        استيقظ|je me reveille
        انهض|je me leve
        انام|je dors
        احلم|je reve
        اغسل وجهي|je lave mon visage
        اغسل اسناني|je brosse mes dents
        استحم|je me douche
        امشط شعري|je me coiffe
        البس ملابسي|j'habille mes vetements
        اخلع حذائي|j'enleve mes chaussures
        افطر|je prends le petit-dejeuner
        اذهب الى المدرسة|je vais a l'ecole
        ارجع|je reviens
        ادرس الدرس|j'etudie la lecon
        اكتب الواجب|j'ecris le devoir
        اقرأ القصة|je lis l'histoire
        اشاهد التلفاز|je regarde la television
        استمع الى الراديو|j'ecoute la radio
        العب|je joue
        امشي قليلا|je marche un peu
        اجلس|je m'assois
        استريح|je me repose
        اطبخ|je cuisine
        انظف|je nettoie
        اتحدث|je parle
        اسال|je demande
        اجيب|je reponds
        افتح|j'ouvre
        اغلق|je ferme
        احمل|je porte
        اضع|je pose
        ابحث|je cherche
        اجد|je trouve
        ارسل|j'envoie
        انتظر الحافلة|j'attends le bus
        اصل|j'arrive
        اغادر|je pars
        ابدا|je commence
        انتهي|je termine
        اتاخر|je suis en retard
        استيقظ مبكرا|je me reveille tot
        مساء كل يوم|chaque soir
        كل صباح|chaque matin
        بعد الظهر|l'apres-midi
        قبل النوم|avant de dormir
        في البيت|a la maison
        في المدرسة|a l'ecole
        في العمل|au travail
        عادة|d'habitude
        احيانا|parfois
        """,
    ),
    _lesson(
        "A1",
        8,
        "Le corps et la sante simple",
        "Corps",
        "Connaitre les parties du corps et quelques mots simples pour parler de son etat.",
        "راسي يؤلمني اليوم قليلا",
        """
        راس|tete
        وجه|visage
        عين|oeil
        انف|nez
        فم|bouche
        اذن|oreille
        سن|dent
        شعر|cheveux
        يد|main
        ذراع|bras
        اصبع|doigt
        صدر|poitrine
        بطن|ventre
        ظهر الجسم|dos
        ساق|jambe
        قدم|pied
        ركبة|genou
        قلب|coeur
        دم|sang
        صحة|sante
        وجع|douleur
        تعب|fatigue
        حمى|fievre
        سعال|toux
        برد|rhume
        دواء|medicament
        راحة|repos
        مريض|malade
        سليم|en bonne sante
        قوي|fort
        ضعيف|faible
        طويل|long
        قصير|court
        جميل|beau
        نحيف|mince
        سمين|gros
        اسنان|dents
        حلق|gorge
        جبين|front
        كتف|epaule
        مرفق|coude
        كاحل|cheville
        جلد|peau
        جرح|blessure
        ضمادة|bandage
        تنفس|respiration
        نبض|pouls
        صداع|mal de tete
        عطس|eternuement
        شفاء|guerison
        """,
    ),
    _lesson(
        "A1",
        9,
        "Les vetements et les couleurs",
        "Vetements",
        "Choisir des vetements, des couleurs et des qualites tres utiles du quotidien.",
        "قميصي الازرق جديد",
        """
        قميص|chemise
        سروال|pantalon
        فستان|robe
        تنورة|jupe
        معطف|manteau
        سترة|veste
        حذاء|chaussure
        جورب|chaussette
        قبعة|casquette
        وشاح|echarpe
        حزام|ceinture
        قفاز|gant
        حقيبة يد|sac a main
        ملابس|vetements
        قماش|tissu
        مقاس|taille
        لون|couleur
        احمر|rouge
        ازرق|bleu
        اخضر|vert
        اصفر|jaune
        ابيض|blanc
        اسود|noir
        بني|marron
        رمادي|gris
        وردي|rose
        برتقالي|orange
        بنفسجي|violet
        فاتح|clair
        غامق|fonce
        انيق|elegant
        مريح|confortable
        ثقيل|lourd
        خفيف|leger
        قصير الكم|a manches courtes
        طويل الكم|a manches longues
        رياضي|sportif
        رسمي|formel
        مخطط|raye
        سادة|uni
        يناسبني|ca me va
        لا يناسبني|ca ne me va pas
        جميل علي|ca me va bien
        في الخزانة|dans l'armoire
        للشتاء|pour l'hiver
        للصيف|pour l'ete
        غسيل|lessive
        كي|repassage
        ازرار|boutons
        سحاب الملابس|fermeture eclair
        """,
    ),
    _lesson(
        "A1",
        10,
        "La meteo, la nature et les loisirs",
        "Loisirs",
        "Observer le temps, la nature et parler de quelques loisirs simples et joyeux.",
        "الطقس جميل في الحديقة",
        """
        شمس|soleil
        قمر|lune
        نجم|etoile
        سماء|ciel
        سحاب|nuage
        مطر|pluie
        رياح|vent
        حر|chaleur
        دفء|douceur
        ظل|ombre
        بحر|mer
        نهر|riviere
        جبل|montagne
        شجرة|arbre
        زهرة|fleur
        عشب|herbe
        رمل|sable
        صحراء|desert
        غابة|foret
        طائر|oiseau
        قطة|chat
        كلب|chien
        سمكة|poisson
        حصان|cheval
        فراشة|papillon
        حديقة صغيرة|petit jardin
        موسم|saison
        ربيع|printemps
        صيف|ete
        خريف|automne
        شتاء|hiver
        نزهة|promenade
        لعبة|jeu
        كرة|ballon
        سباحة|natation
        جري|course
        رسم|dessin
        موسيقى|musique
        اغنية|chanson
        صورة|photo
        كاميرا|camera
        كتاب مصور|livre illustre
        هواية|loisir
        فراغ|temps libre
        عطلة|vacances
        رحلة|sortie
        استمتع|je profite
        اضحك|je ris
        ابتسم|je souris
        اهدأ|je me calme
        """,
    ),
    _lesson(
        "A2",
        1,
        "Faire des achats utiles",
        "Achats",
        "Acheter, comparer des prix et demander ce qu'il faut dans un magasin ou un marche.",
        "كم سعر هذه الحقيبة",
        """
        سعر|prix
        رخيص|bon marche
        غالي|cher
        تخفيض|reduction
        خصم|rabais
        فاتورة|facture
        صندوق الدفع|caisse
        نقدا|en especes
        بطاقة|carte
        عملة|monnaie
        نقود|argent liquide
        صرف|monnaie rendue
        ميزانية|budget
        شراء|achat
        بيع|vente
        زبون|client
        بائع|vendeur
        متجر كبير|grand magasin
        محل ملابس|boutique de vetements
        محل احذية|magasin de chaussures
        سوق شعبي|marche populaire
        سلة|panier
        قائمة المشتريات|liste de courses
        كمية|quantite
        كيلو|kilo
        نصف كيلو|un demi-kilo
        لتر|litre
        عبوة|emballage
        علبة|boite
        قطعة|piece
        زوجان|deux pieces
        مقاس اكبر|taille plus grande
        مقاس اصغر|taille plus petite
        لون اخر|autre couleur
        هل يوجد؟|est-ce qu'il y en a ?
        اريد هذا|je veux ceci
        كم السعر؟|combien ca coute ?
        هذا مناسب|c'est convenable
        هذا مكلف|c'est couteux
        ارخص قليلا|un peu moins cher
        الدفع عندي|j'ai de quoi payer
        الباقي|la monnaie
        وصل|recu
        استبدال|echange
        ارجاع|retour
        مفقود|manquant
        متوفر|disponible
        غير متوفر|indisponible
        مزدحم|bondé
        صف الانتظار|file d'attente
        """,
    ),
    _lesson(
        "A2",
        2,
        "Voyager et se deplacer",
        "Voyage",
        "Comprendre les mots essentiels du voyage, du trajet et du sejour.",
        "حجزت تذكرة للرحلة",
        """
        تذكرة|billet
        حجز|reservation
        جواز سفر|passeport
        حقيبة سفر|valise
        غرفة فندقية|chambre d'hotel
        استقبال|reception
        رحلة جوية|vol
        رحلة برية|trajet terrestre
        منصة|quai
        مقعد|siege
        نافذة الطائرة|hublot
        تاخير|retard
        الغاء|annulation
        موعد الانطلاق|heure de depart
        وقت الوصول|heure d'arrivee
        مسافر|voyageur
        سائح|touriste
        دليل|guide
        محطة القطار|gare
        موقف الحافلات|gare routiere
        بوابة|porte d'embarquement
        رحلة ذهاب|aller simple
        رحلة عودة|retour
        حقائب|bagages
        وزن الامتعة|poids des bagages
        تفتيش|controle
        امن المطار|securite de l'aeroport
        ختم الدخول|tampon d'entree
        تاشيرة|visa
        اقامة|sejour
        حجزت مسبقا|j'ai reserve a l'avance
        اين الفندق؟|ou est l'hotel ?
        اريد دليلا للطريق|je veux un guide pour la route
        كم تبعد؟|a quelle distance ?
        طريق سريع|autoroute
        شارع جانبي|rue secondaire
        ازدحام|embouteillage
        اختصار الطريق|raccourci
        اركب|je monte
        انزل|je descends
        ابدل القطار|je change de train
        افقد الطريق|je perds la route
        اصل متاخرا|j'arrive en retard
        اسافر وحدي|je voyage seul
        مع المجموعة|avec le groupe
        رحلة عمل|voyage d'affaires
        رحلة عائلية|voyage en famille
        منظر جميل|beau paysage
        صورة تذكارية|photo souvenir
        رحال|voyageur aguerri
        """,
    ),
    _lesson(
        "A2",
        3,
        "Travailler et etudier",
        "Travail",
        "Parler du travail, des etudes et des outils utiles dans un cadre simple.",
        "ارسل التقرير بعد الاجتماع",
        """
        وظيفة|emploi
        مهنة|metier
        شركة|entreprise
        مكتب عمل|bureau de travail
        زميل|collegue
        مدير|directeur
        مديرة|directrice
        اجتماع|reunion
        مشروع|projet
        تقرير|rapport
        ملف|dossier
        حاسوب|ordinateur
        طابعة|imprimante
        بريد مهني|courriel professionnel
        تدريب|formation
        خبرة|experience
        مهارة|competence
        مقابلة|entretien
        سيرة ذاتية|CV
        دوام|horaire de travail
        راتب|salaire
        اجازة|conge
        مهمة|tache
        موعد تسليم|date limite
        امتحان|examen
        جامعة|universite
        محاضرة|cours magistral
        مكتبة جامعية|bibliotheque universitaire
        بحث|recherche
        نتيجة|resultat
        شهادة|diplome
        قسم|departement
        تخصص|specialite
        مهندس|ingenieur
        ممرضة|infirmiere
        محاسب|comptable
        مبرمج|developpeur
        ادرس اللغة|j'etudie la langue
        اعمل بدوام كامل|je travaille a temps plein
        اعمل بدوام جزئي|je travaille a temps partiel
        اتعلم بسرعة|j'apprends vite
        احتاج مساعدة|j'ai besoin d'aide
        انهي المهمة|je termine la tache
        اراجع الدرس|je revise la lecon
        انجح في الاختبار|je reussis l'examen
        ارسب في المادة|j'echoue a la matiere
        اشارك في الاجتماع|je participe a la reunion
        ارسل التقرير|j'envoie le rapport
        اطبع الصفحة|j'imprime la page
        اغلق الحاسوب|j'eteins l'ordinateur
        """,
    ),
    _lesson(
        "A2",
        4,
        "Faire des demarches",
        "Demarches",
        "Comprendre les papiers, les demandes et les echanges simples avec une administration.",
        "قدم الوثائق في الشباك",
        """
        موعد اداري|rendez-vous administratif
        استمارة|formulaire
        طلب|demande
        وثيقة|document
        نسخة|copie
        توقيع|signature
        ختم|tampon
        رقم الملف|numero du dossier
        بطاقة الهوية|piece d'identite
        شهادة سكن|attestation de residence
        عقد|contrat
        تسجيل|inscription
        تاكيد|confirmation
        موافقة|accord
        رفض|refus
        ارشيف|archives
        شباك|guichet
        استقبال اداري|accueil administratif
        طابور|file
        دوري|mon tour
        دورك|ton tour
        مساعدة ادارية|aide administrative
        ترجمة رسمية|traduction officielle
        موعد جديد|nouveau rendez-vous
        معلومات ناقصة|informations manquantes
        ملف كامل|dossier complet
        عنوان البريد|adresse postale
        رمز بريدي|code postal
        مكتب البلدية|mairie
        مركز الشرطة|commissariat
        المحكمة|tribunal
        محام|avocat
        تصريح|autorisation
        رخصة|permis
        تجديد|renouvellement
        انتهاء الصلاحية|expiration
        ضريبة|impot
        تامين|assurance
        شكوى|reclamation
        استفسار|demande d'information
        خدمة الزبائن|service client
        اتصل لاحقا|appelez plus tard
        عد غدا|revenez demain
        وقع هنا|signez ici
        اكتب بوضوح|ecrivez clairement
        قدم الوثائق|deposez les documents
        انتظر الرد|attendez la reponse
        تم القبول|accepte
        تم الرفض|refuse
        نسخة اضافية|copie supplementaire
        """,
    ),
    _lesson(
        "A2",
        5,
        "Communiquer avec le numerique",
        "Numerique",
        "Utiliser le vocabulaire simple du telephone, des messages et des applications.",
        "افتح التطبيق ثم ارسل الرسالة",
        """
        هاتف ذكي|smartphone
        رسالة|message
        مكالمة|appel
        رقم الهاتف|numero de telephone
        بريد الكتروني|courriel
        كلمة السر|mot de passe
        حساب|compte
        تطبيق|application
        موقع|site web
        رابط|lien
        شبكة|reseau
        واي فاي|wifi
        شاشة|ecran
        لوحة المفاتيح|clavier
        ماوس|souris
        شاحن|chargeur
        بطارية|batterie
        سماعة|ecouteur
        كاميرا الهاتف|camera du telephone
        تسجيل صوتي|enregistrement audio
        فيديو قصير|courte video
        تنزيل|telechargement
        تحميل|chargement
        تحديث|mise a jour
        مشاركة|partage
        ارسال رسالة|envoyer un message
        رد سريع|reponse rapide
        اتصال ضعيف|connexion faible
        الانترنت بطيء|internet lent
        خارج التغطية|hors reseau
        نغمة|sonnerie
        اشعار|notification
        ملف مرفق|piece jointe
        صورة شخصية|photo de profil
        دردشة|discussion
        مجموعة|groupe
        تسجيل الدخول|connexion
        تسجيل الخروج|deconnexion
        نسيت كلمة السر|j'ai oublie le mot de passe
        انسخ الرابط|copie le lien
        افتح التطبيق|ouvre l'application
        اغلق الهاتف|eteins le telephone
        اشحن البطارية|charge la batterie
        التقط صورة|prends une photo
        احذف الرسالة|supprime le message
        احفظ الملف|enregistre le fichier
        اطبع البريد|imprime le courriel
        ابحث في الموقع|cherche sur le site
        شاشة مكسورة|ecran casse
        جهاز جديد|nouvel appareil
        """,
    ),
    _lesson(
        "A2",
        6,
        "Exprimer des sentiments",
        "Sentiments",
        "Dire ce que l'on ressent, donner un accord simple et nuancer une reaction.",
        "انا سعيد لكنني قلق",
        """
        سعيد|heureux
        حزين|triste
        غاضب|en colere
        قلق|inquiet
        مطمئن|rassure
        متوتر|stresse
        مرتبك|embarrasse
        متحمس|enthousiaste
        خائف|effraye
        فخور|fier
        خجول|timide
        صبور|patient
        كريم|genereux
        لطيف|gentil
        صادق|honnete
        كذاب|menteur
        جاد|serieux
        مرح|joyeux
        نشيط|actif
        كسول|paresseux
        ذكي|intelligent
        حذر|prudent
        متفائل|optimiste
        متشائم|pessimiste
        منزعج|contrarie
        مرتاح|a l'aise
        متعب نفسيا|moralement fatigue
        احب هذا|j'aime ceci
        لا احب ذلك|je n'aime pas cela
        افضل القهوة|je prefere le cafe
        اكره الضوضاء|je deteste le bruit
        اشعر بالجوع|je ressens la faim
        اشعر بالبرد|j'ai froid
        انا مستغرب|je suis surpris
        انا مشغول|je suis occupe
        انا حر اليوم|je suis libre aujourd'hui
        يبدو سعيدا|il a l'air heureux
        تبدو متعبة|elle a l'air fatiguee
        هذا يزعجني|cela me derange
        هذا يعجبني|cela me plait
        رايي مختلف|mon avis differe
        في نظري|a mon avis
        ربما انت محق|peut-etre que tu as raison
        لا اعتقد ذلك|je ne pense pas
        انا موافق|je suis d'accord
        انا غير موافق|je ne suis pas d'accord
        لا مشكلة عندي|je n'ai pas de probleme
        هذا مهم جدا|c'est tres important
        الامر عادي|c'est normal
        ما رايك؟|qu'en penses-tu ?
        """,
    ),
    _lesson(
        "A2",
        7,
        "Aller chez le medecin",
        "Sante",
        "Prendre un rendez-vous, expliquer une douleur simple et suivre des consignes basiques.",
        "حجزت موعد الطبيب غدا",
        """
        عيادة|cabinet medical
        موعد الطبيب|rendez-vous chez le medecin
        فحص|examen
        تحليل|analyse
        وصفة طبية|ordonnance
        صيدلي|pharmacien
        اسعاف|ambulance
        طوارئ|urgences
        ضغط الدم|tension arterielle
        سكر الدم|glycemie
        حرارة الجسم|temperature du corps
        التهاب|inflammation
        حساسية|allergie
        صداع شديد|fort mal de tete
        الم الاسنان|mal aux dents
        الم الظهر|douleur au dos
        الم المعدة|mal d'estomac
        دوخة|vertige
        غثيان|nausee
        ادوية|medicaments
        حبوب|comprimes
        شراب طبي|sirop
        حقنة|piqure
        ضماد|pansement
        عملية|operation
        استراحة مرضية|arret maladie
        موعد المتابعة|rendez-vous de suivi
        غرفة الانتظار|salle d'attente
        جهاز قياس|appareil de mesure
        تنفس عميق|respire profondement
        افتح فمك|ouvrez la bouche
        خذ الدواء|prenez le medicament
        مرتان يوميا|deux fois par jour
        قبل الاكل|avant de manger
        بعد الاكل|apres le repas
        اشرب ماء كثيرا|bois beaucoup d'eau
        تحتاج راحة|tu as besoin de repos
        لا تقلق|ne t'inquiete pas
        هل لديك تامين؟|avez-vous une assurance ?
        اين يؤلمك؟|ou avez-vous mal ?
        منذ متى؟|depuis quand ?
        تحسن بسيط|legere amelioration
        لا اشعر بتحسن|je ne vais pas mieux
        اتصل بالطبيب|appelle le medecin
        احجز موعدا|prends rendez-vous
        نتيجة التحليل|resultat de l'analyse
        اشعة|radiographie
        كسر|fracture
        اسنان حساسة|dents sensibles
        علاج|traitement
        """,
    ),
    _lesson(
        "A2",
        8,
        "Habiter, entretenir, reparer",
        "Habitat",
        "Parler d'un logement, d'un probleme domestique et d'une petite reparation.",
        "يحتاج البيت الى صيانة",
        """
        ايجار|loyer
        مالك البيت|proprietaire
        عقد الايجار|bail
        شقة|appartement
        بناية|immeuble
        مصعد|ascenseur
        مدخل العمارة|entree de l'immeuble
        موقف السيارات|parking
        فاتورة الكهرباء|facture d'electricite
        فاتورة الماء|facture d'eau
        صيانة|maintenance
        اصلاح|reparation
        سباك|plombier
        كهربائي|electricien
        نجار|menuisier
        تسرب|fuite
        عطل|panne
        مصباح|ampoule
        مقبس|prise electrique
        سخان|chauffe-eau
        غسالة|machine a laver
        ثلاجة كبيرة|grand refrigerateur
        فرن كهربائي|four electrique
        مروحة|ventilateur
        مكيف|climatiseur
        ستارة جديدة|nouveau rideau
        سجادة|tapis
        رف|etagere
        صندوق|boite
        ادوات التنظيف|produits de nettoyage
        صابون|savon
        منظف|detergent
        ممسحة|serpillere
        نفايات|dechets
        اعادة التدوير|recyclage
        ترتيب البيت|rangement de la maison
        اصلح الباب|je repare la porte
        غير المصباح|change l'ampoule
        افتح النافذة|ouvre la fenetre
        اغلق الماء|ferme l'eau
        نظف المطبخ|nettoie la cuisine
        انقل الصندوق|deplace la boite
        ارفع الكرسي|leve la chaise
        ضع الاغراض|range les affaires
        البيت ضيق|la maison est etroite
        البيت واسع|la maison est spacieuse
        الجيران مزعجون|les voisins sont bruyants
        المكان مريح|l'endroit est confortable
        احتاج صيانة|j'ai besoin de maintenance
        تم الاصلاح|c'est repare
        """,
    ),
    _lesson(
        "A2",
        9,
        "Sortir et participer",
        "Relations",
        "Accepter une invitation, se retrouver et parler d'une sortie simple entre proches.",
        "سنلتقي في المقهى مساء",
        """
        دعوة|invitation
        حفلة|fete
        عيد ميلاد|anniversaire
        زفاف|mariage
        زيارة|visite
        ضيف|invite
        هدية|cadeau
        مطعم هادئ|restaurant calme
        مقهى|cafe
        سينما|cinema
        مسرح|theatre
        معرض|exposition
        مباراة|match
        فريق|equipe
        جمهور|public
        موعد صديق|rendez-vous avec un ami
        نتقابل مساء|on se retrouve ce soir
        تاخرت قليلا|je suis un peu en retard
        ساصل قريبا|j'arrive bientot
        هل انت متفرغ؟|es-tu disponible ?
        اراك هناك|je te vois la-bas
        شكرا على الدعوة|merci pour l'invitation
        يسعدني الحضور|je suis heureux de venir
        لا استطيع الحضور|je ne peux pas venir
        في نهاية الاسبوع|le week-end
        مساء الجمعة|vendredi soir
        بعد العمل|apres le travail
        قبل الحفلة|avant la fete
        طاولة محجوزة|table reservee
        قائمة الطعام|menu
        صورة جماعية|photo de groupe
        موسيقى هادئة|musique douce
        رقص|danse
        تصفيق|applaudissements
        محادثة طويلة|longue conversation
        جار قديم|ancien voisin
        علاقة طيبة|bonne relation
        زميل سابق|ancien collegue
        جارتي|ma voisine
        ابن عمي|mon cousin paternel
        صديقتي الجديدة|ma nouvelle amie
        ارسل العنوان|envoie l'adresse
        شاركني الموقع|partage-moi la localisation
        الجو جميل الليلة|il fait beau ce soir
        نحتفل معا|nous fetons ensemble
        كانت سهرة جميلة|c'etait une belle soiree
        استمتعنا كثيرا|nous avons beaucoup profite
        اراك لاحقا|je te vois plus tard
        سلامي للجميع|mes salutations a tous
        اهلا بالضيوف|bienvenue aux invites
        """,
    ),
    _lesson(
        "A2",
        10,
        "Donner son avis et faire des projets",
        "Opinions",
        "Exprimer une opinion simple, expliquer une idee et parler d'un projet proche.",
        "في رايي هذه خطة جيدة",
        """
        اخطط|je planifie
        اقرر|je decide
        احاول|j'essaie
        اتعلم اكثر|j'apprends davantage
        اتذكر|je me souviens
        انسى|j'oublie
        اوافق|j'approuve
        اعترض|je m'oppose
        اقترح|je propose
        اناقش|je discute
        اقارن|je compare
        اختار|je choisis
        افضل|je prefere
        احتاج الى وقت|j'ai besoin de temps
        اريد ان اغير|je veux changer
        يمكنني ان اساعد|je peux aider
        يجب ان اذهب|je dois partir
        لا بد من العمل|il faut travailler
        من الممكن ان نبدأ|il est possible de commencer
        الهدف واضح|l'objectif est clair
        خطة بسيطة|plan simple
        خطوة اولى|premiere etape
        خطوة ثانية|deuxieme etape
        نتيجة جيدة|bon resultat
        سبب مقنع|raison convaincante
        مثال واضح|exemple clair
        فكرة جديدة|idee nouvelle
        حل مناسب|solution adaptee
        مشكلة معقدة|probleme complexe
        راي شخصي|avis personnel
        حسب التجربة|selon l'experience
        في المستقبل|dans l'avenir
        الاسبوع المقبل|la semaine prochaine
        الشهر القادم|le mois prochain
        بعد قليل|dans un instant
        في البداية|au debut
        في النهاية|a la fin
        على سبيل المثال|par exemple
        بشكل عام|en general
        مرة ثانية|une deuxieme fois
        لا يزال الوقت مبكرا|il est encore tot
        الامر يستحق|cela en vaut la peine
        هذا افضل حل|c'est la meilleure solution
        لست متاكدا تماما|je ne suis pas totalement sur
        دعنا نحاول|essayons
        لماذا لا؟|pourquoi pas ?
        اتمنى النجاح|j'espere la reussite
        اريد ممارسة العربية|je veux pratiquer l'arabe
        ساعود لاحقا|je reviendrai plus tard
        انتهى الامر|c'est termine
        """,
    ),
]


def transliterate_arabic(text):
    return " ".join("".join(_ARABIC_TO_LATIN.get(char, "") for char in text).split())


def build_example_phrase(lesson_spec, term):
    template = _THEME_TEMPLATES[lesson_spec["theme"]]
    return template.format(term=term)


def _preview_terms(lesson_spec):
    return " - ".join(entry["mot_arabe"] for entry in lesson_spec["entries"][:6])


def build_lesson_content(lesson_spec):
    return (
        '<div class="arabic-content">'
        f"<p>{lesson_spec['model_sentence']}</p>"
        f"<p>{_preview_terms(lesson_spec)}</p>"
        "</div>"
        f"<p>{lesson_spec['goal']} Travaillez 50 entrees utiles avec une progression douce.</p>"
    )


def _ordre_mots_variants(sentence):
    words = sentence.split()
    reversed_words = " ".join(reversed(words))
    truncated = " ".join(words[:-1]) if len(words) > 1 else sentence
    rotated = " ".join(words[1:] + words[:1]) if len(words) > 1 else sentence
    variants = []
    for item in (sentence, reversed_words, truncated, rotated):
        if item and item not in variants:
            variants.append(item)
    while len(variants) < 4:
        variants.append(f"{sentence} {len(variants)}")
    return variants[:4]


def build_lesson_questions(lesson_spec):
    entries = lesson_spec["entries"]
    qcm_target = entries[0]
    qcm_distractors = entries[1:4]
    ecoute_target = entries[4]
    ecoute_distractors = entries[5:8]
    dictee_target = entries[8]
    ordre_variants = _ordre_mots_variants(lesson_spec["model_sentence"])

    return [
        {
            "ordre": 1,
            "texte": f'Choisissez le mot arabe pour "{qcm_target["traduction_fr"]}".',
            "type_exercice": "qcm",
            "audio_url": None,
            "bonne_reponse_texte": None,
            "choix": [
                {"texte": qcm_target["mot_arabe"], "est_correct": True, "audio_url": None},
                *[
                    {"texte": item["mot_arabe"], "est_correct": False, "audio_url": None}
                    for item in qcm_distractors
                ],
            ],
        },
        {
            "ordre": 2,
            "texte": "Ecoutez et choisissez le bon mot.",
            "type_exercice": "ecoute",
            "audio_url": None,
            "bonne_reponse_texte": ecoute_target["mot_arabe"],
            "choix": [
                {"texte": ecoute_target["mot_arabe"], "est_correct": True, "audio_url": None},
                *[
                    {"texte": item["mot_arabe"], "est_correct": False, "audio_url": None}
                    for item in ecoute_distractors
                ],
            ],
        },
        {
            "ordre": 3,
            "texte": "Remettez la phrase dans l'ordre.",
            "type_exercice": "ordre_mots",
            "audio_url": None,
            "bonne_reponse_texte": lesson_spec["model_sentence"],
            "choix": [
                {"texte": ordre_variants[0], "est_correct": True, "audio_url": None},
                {"texte": ordre_variants[1], "est_correct": False, "audio_url": None},
                {"texte": ordre_variants[2], "est_correct": False, "audio_url": None},
                {"texte": ordre_variants[3], "est_correct": False, "audio_url": None},
            ],
        },
        {
            "ordre": 4,
            "texte": "Dictee : ecrivez le mot entendu.",
            "type_exercice": "dictee",
            "audio_url": None,
            "bonne_reponse_texte": dictee_target["mot_arabe"],
            "choix": [],
        },
    ]


def build_placement_specs():
    a1_lessons = [lesson for lesson in PEDAGOGICAL_LESSON_SPECS if lesson["level"] == "A1"]
    a2_lessons = [lesson for lesson in PEDAGOGICAL_LESSON_SPECS if lesson["level"] == "A2"]
    selected_lessons = [a1_lessons[index] for index in (0, 2, 4, 6, 8)] + [
        a2_lessons[index] for index in (0, 2, 4, 6, 8)
    ]

    placement_specs = []
    for order, lesson_spec in enumerate(selected_lessons, start=1):
        target = lesson_spec["entries"][0]
        distractors = lesson_spec["entries"][1:4]
        placement_specs.append(
            {
                "order": order,
                "level": lesson_spec["level"],
                "texte": f'Que veut dire "{target["mot_arabe"]}" ?',
                "type_question": "qcm",
                "audio_url": None,
                "image_url": None,
                "choices": [
                    {"texte": target["traduction_fr"], "est_correct": True, "image_url": None},
                    *[
                        {"texte": item["traduction_fr"], "est_correct": False, "image_url": None}
                        for item in distractors
                    ],
                ],
            }
        )
    return placement_specs


def _validate_specs():
    if len(PEDAGOGICAL_LESSON_SPECS) != 20:
        raise ValueError("Le seed pedagogique doit contenir exactement 20 lecons.")

    all_terms = []
    per_level = {"A1": 0, "A2": 0}
    level_lesson_counts = {"A1": 0, "A2": 0}
    for lesson_spec in PEDAGOGICAL_LESSON_SPECS:
        if len(lesson_spec["entries"]) != 50:
            raise ValueError(f'La lecon "{lesson_spec["title"]}" doit contenir exactement 50 entrees.')
        level_lesson_counts[lesson_spec["level"]] += 1
        per_level[lesson_spec["level"]] += len(lesson_spec["entries"])
        all_terms.extend(entry["mot_arabe"] for entry in lesson_spec["entries"])

    if level_lesson_counts != {"A1": 10, "A2": 10}:
        raise ValueError("Le seed pedagogique doit contenir 10 lecons A1 et 10 lecons A2.")
    if per_level != {"A1": 500, "A2": 500}:
        raise ValueError("Le seed pedagogique doit contenir 500 entrees A1 et 500 entrees A2.")
    if len(set(all_terms)) != len(all_terms):
        duplicates = []
        seen = set()
        for term in all_terms:
            if term in seen and term not in duplicates:
                duplicates.append(term)
            seen.add(term)
        raise ValueError(f"Termes arabes dupliques dans le seed: {', '.join(duplicates[:20])}")


_validate_specs()


def _sync_choices(question, desired_choices, ChoiceModel):
    existing_choices = sorted(question.choix, key=lambda item: item.id)
    for index, choice_spec in enumerate(desired_choices):
        if index < len(existing_choices):
            choice = existing_choices[index]
        else:
            choice = ChoiceModel(question_id=question.id)
            db.session.add(choice)
            existing_choices.append(choice)
        choice.texte = choice_spec["texte"]
        choice.est_correct = bool(choice_spec["est_correct"])
        if hasattr(choice, "audio_url"):
            choice.audio_url = _merge_audio_url(choice.audio_url, choice_spec.get("audio_url"))
        if hasattr(choice, "image_url"):
            choice.image_url = choice_spec.get("image_url")

    for extra_choice in existing_choices[len(desired_choices):]:
        db.session.delete(extra_choice)


def _find_or_create_course(course_spec, CourseModel, teacher_id=None):
    course = CourseModel.query.filter_by(nom=course_spec["name"]).first()
    if course is None:
        for legacy_image_url in course_spec.get("legacy_image_urls", []):
            course = CourseModel.query.filter_by(image_url=legacy_image_url).first()
            if course is not None:
                break

    if course is None:
        course = CourseModel(
            nom=course_spec["name"],
            niveau=course_spec["level"],
            image_url=course_spec["image_url"],
            est_publie=True,
        )
        db.session.add(course)
        db.session.flush()

    course.nom = course_spec["name"]
    course.description = course_spec["description"]
    course.niveau = course_spec["level"]
    course.image_url = course_spec["image_url"]
    course.est_publie = True
    if teacher_id is not None:
        course.enseignant_id = teacher_id
    return course


def _cleanup_legacy_demo_courses(CourseModel):
    for course in CourseModel.query.all():
        if course.nom in PEDAGOGICAL_COURSE_NAMES:
            continue
        if course.nom in PEDAGOGICAL_LEGACY_COURSE_NAMES or course.image_url in PEDAGOGICAL_LEGACY_COURSE_IMAGE_URLS:
            db.session.delete(course)


def _merge_audio_url(existing_audio_url, desired_audio_url):
    if desired_audio_url is not None:
        return (desired_audio_url or "").strip() or None
    return (existing_audio_url or "").strip() or None


def seed_pedagogical_content(*, enseignant_demo=None):
    from .models import Choix, Cours, Lecon, PlacementChoix, PlacementQuestion, PlacementTest, Question, Vocabulaire

    teacher_id = enseignant_demo.id if enseignant_demo is not None else None

    for lesson_spec in PEDAGOGICAL_LESSON_SPECS:
        for entry in lesson_spec["entries"]:
            vocabulaire = Vocabulaire.query.filter_by(mot_arabe=entry["mot_arabe"]).first()
            if vocabulaire is None:
                vocabulaire = Vocabulaire(mot_arabe=entry["mot_arabe"])
                db.session.add(vocabulaire)
            existing_audio_url = vocabulaire.audio_url
            vocabulaire.translitteration = transliterate_arabic(entry["mot_arabe"]) or None
            vocabulaire.traduction_fr = entry["traduction_fr"]
            vocabulaire.traduction_en = None
            vocabulaire.traduction_es = None
            vocabulaire.audio_url = existing_audio_url or None
            vocabulaire.exemple_phrase = build_example_phrase(lesson_spec, entry["mot_arabe"])
            vocabulaire.niveau_cefr = lesson_spec["level"]
            vocabulaire.theme = lesson_spec["theme"]
            vocabulaire.est_pedagogique = True

    course_specs_by_name = {spec["name"]: spec for spec in PEDAGOGICAL_COURSE_SPECS}
    lessons_by_course = {spec["name"]: [] for spec in PEDAGOGICAL_COURSE_SPECS}
    for lesson_spec in PEDAGOGICAL_LESSON_SPECS:
        lessons_by_course[lesson_spec["course_name"]].append(lesson_spec)

    for course_name, lesson_specs in lessons_by_course.items():
        course_spec = course_specs_by_name[course_name]
        course = _find_or_create_course(course_spec, Cours, teacher_id=teacher_id)

        existing_lessons_by_order = {lesson.ordre: lesson for lesson in course.lecons}
        desired_orders = set()
        for lesson_spec in sorted(lesson_specs, key=lambda item: item["order"]):
            desired_orders.add(lesson_spec["order"])
            lesson = existing_lessons_by_order.get(lesson_spec["order"])
            if lesson is None:
                lesson = Lecon(
                    cours_id=course.id,
                    ordre=lesson_spec["order"],
                    titre=lesson_spec["title"],
                    est_publie=True,
                )
                db.session.add(lesson)
                db.session.flush()

            lesson.titre = lesson_spec["title"]
            lesson.ordre = lesson_spec["order"]
            lesson.contenu_texte = build_lesson_content(lesson_spec)
            lesson.video_url = None
            lesson.pdf_url = course_spec["pdf_url"]
            lesson.audio_url = _merge_audio_url(lesson.audio_url, None)
            lesson.duree_minutes = 18 if lesson_spec["level"] == "A1" else 22
            lesson.points_recompense = 18 if lesson_spec["level"] == "A1" else 24
            lesson.est_publie = True
            lesson.date_publication = lesson.date_publication or datetime.utcnow()

            desired_questions = build_lesson_questions(lesson_spec)
            existing_questions_by_order = {question.ordre: question for question in lesson.questions}
            desired_question_orders = set()
            for question_spec in desired_questions:
                desired_question_orders.add(question_spec["ordre"])
                question = existing_questions_by_order.get(question_spec["ordre"])
                if question is None:
                    question = Question(
                        lecon_id=lesson.id,
                        ordre=question_spec["ordre"],
                        texte=question_spec["texte"],
                    )
                    db.session.add(question)
                    db.session.flush()

                question.ordre = question_spec["ordre"]
                question.texte = question_spec["texte"]
                question.type_exercice = question_spec["type_exercice"]
                question.audio_url = _merge_audio_url(question.audio_url, question_spec.get("audio_url"))
                question.bonne_reponse_texte = question_spec.get("bonne_reponse_texte")
                _sync_choices(question, question_spec.get("choix", []), Choix)

            for existing_question in list(lesson.questions):
                if existing_question.ordre not in desired_question_orders:
                    db.session.delete(existing_question)

        for existing_lesson in list(course.lecons):
            if existing_lesson.ordre not in desired_orders:
                db.session.delete(existing_lesson)

    _cleanup_legacy_demo_courses(Cours)

    seeded_course_ids = [course.id for course in Cours.query.filter(Cours.nom.in_(PEDAGOGICAL_COURSE_NAMES)).all()]
    seeded_lesson_ids = {
        lesson.id for lesson in Lecon.query.filter(Lecon.cours_id.in_(seeded_course_ids)).all()
    }
    for stray_question in Question.query.all():
        if stray_question.lecon_id not in seeded_lesson_ids:
            db.session.delete(stray_question)

    tests = PlacementTest.query.order_by(PlacementTest.id.asc()).all()
    if tests:
        placement_test = tests[0]
        for extra_test in tests[1:]:
            db.session.delete(extra_test)
    else:
        placement_test = PlacementTest()
        db.session.add(placement_test)
        db.session.flush()

    existing_placement_by_order = {question.ordre: question for question in placement_test.questions}
    desired_placement_orders = set()
    for placement_spec in build_placement_specs():
        desired_placement_orders.add(placement_spec["order"])
        question = existing_placement_by_order.get(placement_spec["order"])
        if question is None:
            question = PlacementQuestion(
                test_id=placement_test.id,
                ordre=placement_spec["order"],
                texte=placement_spec["texte"],
                type_question=placement_spec["type_question"],
            )
            db.session.add(question)
            db.session.flush()

        question.ordre = placement_spec["order"]
        question.texte = placement_spec["texte"]
        question.type_question = placement_spec["type_question"]
        question.audio_url = _merge_audio_url(question.audio_url, placement_spec.get("audio_url"))
        question.image_url = placement_spec.get("image_url")
        _sync_choices(question, placement_spec["choices"], PlacementChoix)

    for existing_question in list(placement_test.questions):
        if existing_question.ordre not in desired_placement_orders:
            db.session.delete(existing_question)
