# Usage légal et éthique — à lire avant toute enquête

Ce projet automatise l'agrégation de **renseignement en sources ouvertes** sur
des personnes. L'automatisation ne change rien à vos obligations : elle les rend
seulement plus faciles à enfreindre vite et à grande échelle. Lisez cette page.

## Pour quoi c'est fait

- évaluations de sécurité que vous êtes **mandaté ou autorisé** à réaliser
  (périmètre / règles d'engagement signés) ;
- cartographie de **votre propre** empreinte numérique ou de celle de votre
  organisation, de vos proches à leur demande ;
- exercices CTF / Trace Labs (personnes disparues) / laboratoire / formation ;
- renseignement sur les menaces, protection de marque, lutte anti-fraude ;
- journalisme et recherche, dans le respect du droit applicable.

## Pour quoi c'est **interdit**

- traquer, harceler, intimider, surveiller, « doxxer » qui que ce soit ;
- constituer un fichier sur des personnes sans base légale ;
- prendre des décisions à leur égard (embauche, crédit, location…) sur la base de
  ce rapport ;
- toute finalité que la personne concernée trouverait déraisonnable si elle
  l'apprenait.

## Cadre — France / UE (non exhaustif, pas un avis juridique)

| Sujet | Référence | En clair |
|---|---|---|
| Traitement de données personnelles | RGPD art. 5, 6, 14 ; Loi Informatique et Libertés | Il faut une **base légale** (consentement, contrat, obligation légale, **intérêt légitime** documenté et mis en balance). Minimisez, limitez la conservation, informez quand c'est requis, respectez les droits d'accès/effacement. |
| Données « sensibles » | RGPD art. 9 | Opinions, santé, orientation, religion, syndicat… : interdit sauf exceptions étroites. Ne les collectez pas. |
| Collecte déloyale | Code pénal art. 226-18 | Collecter des données personnelles par un moyen frauduleux, déloyal ou illicite est un délit. |
| Harcèlement | Code pénal art. 222-33-2-2 | Propos/comportements répétés dégradant les conditions de vie d'autrui. |
| Usurpation d'identité en ligne | Code pénal art. 226-4-1 | Usurper l'identité d'un tiers ou faire usage de ses données pour troubler sa tranquillité. |
| Atteinte à un STAD | Code pénal art. 323-1 s. | Accès/maintien frauduleux dans un système : le scan actif (`--active`) sans autorisation peut tomber sous le coup de ces articles. |
| Atteinte à la vie privée | Code pénal art. 226-1 s. ; Code civil art. 9 | Domicile, localisation, vie familiale : particulièrement protégés. |

Équivalents ailleurs : Computer Misuse Act (UK), CFAA (US), etc.

## La fonction « famille / proches » (`--relations`)

Elle est **désactivée par défaut**. L'activer (`--relations`, ou
`OSINT_ALLOW_RELATIONS=1`) revient à affirmer que :

1. vous avez une base légale pour traiter des données concernant des personnes
   qui **ne sont pas votre cible** et n'ont rien demandé ;
2. votre finalité couvre explicitement l'entourage (ex. enquête Trace Labs sur
   une disparition, due diligence avec périmètre incluant les bénéficiaires
   effectifs, cartographie familiale demandée par la personne elle-même) ;
3. vous n'en ferez rien qui puisse nuire à ces tiers.

Les liens familiaux produits sont **déduits de mentions publiques et non
vérifiés**. Chaque champ du dossier porte un niveau de confiance
(`sûr` / `probable` / `piste`). Une « piste » n'est pas un fait.

## Ce que ce projet ne fait pas

- pas d'exploitation, de force brute, de bourrage d'identifiants, de logiciel
  malveillant ;
- pas de contournement d'authentification ni de CAPTCHA, pas d'évasion de
  détection ;
- pas de scraping derrière authentification ni en violation manifeste des CGU
  (la recherche se limite aux moteurs publics et aux API ouvertes) ;
- pas d'aide au ciblage de masse ;
- l'autopilote reste **toujours passif** ; `--active` (nmap) n'existe que sur
  `osint domain` / `osint ip`, avec avertissement.

## Vos réflexes

- **Périmètre écrit** avant de commencer. Notez la base légale dans le nom de
  l'enquête ou un fichier `NOTES` du dossier.
- **Minimisez** : n'activez `--relations` et n'augmentez `--depth` que si c'est
  nécessaire.
- **Purgez** : `osint case purge <id>` dès que l'enquête n'est plus utile.
  Activez la conservation limitée : `OSINT_CASE_TTL_DAYS=30` +
  `systemctl enable --now osint-case-gc.timer`.
- **Cadence / CGU** : respectez les limites de débit des sources.
- En cas de doute sur la licéité : demandez un avis juridique **avant**.

## Avertissement

Fourni « tel quel » sous licence MIT, sans garantie. Les auteurs déclinent toute
responsabilité en cas d'usage abusif ou de dommage. L'installation et
l'utilisation valent acceptation de ces conditions.
