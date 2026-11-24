"""Veille des règles de Ligne 4.

Relit chaque source de sources.json, compare avec etat.json et ouvre un
ticket GitHub quand un document officiel a changé. Aucune dépendance :
uniquement la bibliothèque standard de Python.

Usage : python veille/veille.py [verifier|rappel]
"""
import datetime as dt
import hashlib
import html.parser
import json
import os
import re
import sys
import urllib.parse
import urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.join(ICI, "sources.json")
ETAT = os.path.join(ICI, "etat.json")
UA = "Mozilla/5.0 (veille-regles Ligne 4; +https://lab.codexmental.com)"
EXT_DOCS = (".pdf", ".csv", ".xlsx", ".xls", ".zip", ".xml", ".txt")
ECHECS_AVANT_ALERTE = 3

# Dates et heures souvent ajoutées automatiquement aux exports : on les ignore
DATES = re.compile(
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?|\d{2}/\d{2}/\d{4}( \d{2}:\d{2}(:\d{2})?)?"
)


def maintenant():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def telecharger(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


class Liens(html.parser.HTMLParser):
    def __init__(self, base):
        super().__init__()
        self.base, self.liens = base, set()

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if not href:
            return
        absolu = urllib.parse.urljoin(self.base, href.strip())
        chemin = urllib.parse.urlparse(absolu).path.lower()
        if (chemin.endswith(EXT_DOCS) or "_extractions.php" in absolu
                or "/sites/default/files/" in absolu or "resources.fina.org" in absolu):
            self.liens.add(absolu)


def empreinte(source, octets):
    """Renvoie (empreinte, détail) : le détail sert à expliquer le changement."""
    if source["mode"] == "liens":
        p = Liens(source["url"])
        p.feed(octets.decode("utf-8", "replace"))
        liens = sorted(p.liens)
        return hashlib.sha256("\n".join(liens).encode()).hexdigest(), liens
    texte = octets.decode("utf-8", "replace") if not octets.startswith(b"%PDF") else None
    if texte is not None:
        texte = DATES.sub("", texte).replace("\r\n", "\n").strip()
        return hashlib.sha256(texte.encode()).hexdigest(), None
    return hashlib.sha256(octets).hexdigest(), None


def ouvrir_ticket(titre, corps):
    jeton, depot = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if not jeton or not depot:
        print("--- ticket (hors GitHub) ---\n" + titre + "\n" + corps)
        return
    req = urllib.request.Request(
        f"https://api.github.com/repos/{depot}/issues",
        data=json.dumps({"title": titre, "body": corps, "labels": ["veille-regles"]}).encode(),
        headers={"Authorization": f"Bearer {jeton}", "Accept": "application/vnd.github+json",
                 "User-Agent": UA, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        print("Ticket ouvert :", json.load(r).get("html_url"))


def charger_etat():
    if os.path.exists(ETAT):
        with open(ETAT, encoding="utf-8") as f:
            return json.load(f)
    return {"sources": {}}


def enregistrer_etat(etat):
    with open(ETAT, "w", encoding="utf-8") as f:
        json.dump(etat, f, ensure_ascii=False, indent=1)
        f.write("\n")


def verifier():
    with open(SOURCES, encoding="utf-8") as f:
        sources = [s for s in json.load(f)["sources"] if s.get("actif") and s.get("url")]
    etat = charger_etat()
    premiere_fois = "derniere_execution" not in etat
    for s in sources:
        e = etat["sources"].setdefault(s["id"], {})
        try:
            octets = telecharger(s["url"])
            h, detail = empreinte(s, octets)
            if detail is not None and not detail:
                raise ValueError("aucun document trouvé sur la page (mise en page changée ?)")
        except Exception as err:  # site indisponible, adresse changée...
            e["echecs"] = e.get("echecs", 0) + 1
            print(f"[{s['id']}] inaccessible ({e['echecs']}) : {err}")
            if e["echecs"] == ECHECS_AVANT_ALERTE:
                ouvrir_ticket(
                    f"Veille : source inaccessible — {s['nom']}",
                    f"La source **{s['nom']}** ({s['pack']}) ne répond plus depuis {ECHECS_AVANT_ALERTE} vérifications.\n\n"
                    f"Adresse : {s['url']}\nDernière erreur : `{err}`\n\n"
                    "L'adresse a peut-être changé : vérifier sur le site officiel et corriger `veille/sources.json`.",
                )
            continue
        e["echecs"] = 0
        e["derniere_lecture"] = maintenant()
        if "empreinte" not in e:
            print(f"[{s['id']}] première lecture, référence enregistrée")
        elif e["empreinte"] != h:
            print(f"[{s['id']}] CHANGEMENT détecté")
            corps = (f"Un document surveillé a changé : **{s['nom']}** (pack {s['pack']}).\n\n"
                     f"Adresse : {s['url']}\nDernière version connue : {e.get('depuis', '?')}\n\n")
            if detail is not None:
                avant = set(e.get("liens", []))
                ajouts, retraits = sorted(set(detail) - avant), sorted(avant - set(detail))
                if ajouts:
                    corps += "Nouveaux documents :\n" + "\n".join(f"- {u}" for u in ajouts) + "\n\n"
                if retraits:
                    corps += "Documents retirés :\n" + "\n".join(f"- {u}" for u in retraits) + "\n\n"
            corps += ("À faire : ouvrir le document, vérifier si les règles de Ligne 4 sont concernées "
                      "(cotation, catégories, épreuves, Interclubs…), puis mettre le pack à jour ou fermer ce ticket "
                      "s'il ne change rien.")
            ouvrir_ticket(f"Veille : changement — {s['nom']}", corps)
            e["depuis"] = maintenant()
        else:
            print(f"[{s['id']}] inchangé")
        if e.get("empreinte") != h:
            e["empreinte"] = h
            e.setdefault("depuis", maintenant())
        if detail is not None:
            e["liens"] = detail
    if premiere_fois:
        lignes = []
        for s in sources:
            e = etat["sources"].get(s["id"], {})
            ok = "empreinte" in e
            lignes.append(f"- {'✅' if ok else '⚠️'} {s['nom']} ({s['pack']})" + ("" if ok else " : inaccessible pour l'instant"))
        ouvrir_ticket(
            "Veille des règles en place",
            "La veille des règles de Ligne 4 a fait sa première lecture. Elle repassera le 3 de chaque mois "
            "et ouvrira un ticket si un document change.\n\n" + "\n".join(lignes) +
            "\n\nSi ce ticket est arrivé par mail, les alertes arriveront aussi. Ce ticket peut être fermé.",
        )
    etat["derniere_execution"] = maintenant()  # garde le dépôt actif (GitHub coupe les tâches après 60 jours sans activité)
    enregistrer_etat(etat)


def rappel():
    an = dt.date.today().year
    ouvrir_ticket(
        f"Veille : confirmer les packs pour la saison {an}-{an + 1}",
        "Nouvelle saison : vérifier que les packs de règles de Ligne 4 sont toujours à jour.\n\n"
        "- [ ] FFN : table de cotation, catégories d'âge, épreuves, Interclubs\n"
        "- [ ] FFN Maîtres : coefficients, règlement\n"
        "- [ ] International : temps de base World Aquatics de la saison\n\n"
        "Si rien n'a changé : confirmer les packs pour la nouvelle saison, puis fermer ce ticket.",
    )
    etat = charger_etat()
    etat["dernier_rappel"] = maintenant()
    enregistrer_etat(etat)


if __name__ == "__main__":
    {"verifier": verifier, "rappel": rappel}[sys.argv[1] if len(sys.argv) > 1 else "verifier"]()
