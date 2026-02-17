# Dictation

Outil de dictée vocale pour Ubuntu 24.04+ (Wayland/GNOME).

Appuyez sur un raccourci clavier, dictez, et le texte transcrit est copié dans le presse-papier.

## Installation

```bash
git clone git@github.com:florentdestremau/dictation.git
cd dictation
./install.sh
```

Le script installe les dépendances, crée l'environnement virtuel et configure le raccourci clavier **Alt+D**.

Par défaut la transcription est locale via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (modèle `small`). Le modèle est téléchargé automatiquement au premier lancement (~500 Mo).

## Utilisation

1. **Alt+D** : ouvre la fenêtre en mode enregistrement
2. **Parlez** dans le micro
3. **Entrée** : arrête l'enregistrement et lance la transcription
4. Le texte s'affiche, vous pouvez l'éditer
5. **Entrée** : copie dans le presse-papier et ferme
6. **Échap** : ferme sans copier
7. **Alt+D** (fenêtre ouverte) : ferme la fenêtre

## Utiliser Groq au lieu du modèle local

Pour une transcription plus rapide via l'API [Groq](https://console.groq.com) (gratuit) :

1. Créer une clé API sur [console.groq.com](https://console.groq.com)
2. Créer un fichier `.env` :

```
GROQ_API_KEY=gsk_votre_cle_ici
```

3. Créer un fichier `config.json` :

```json
{
  "backend": "groq",
  "groq_model": "whisper-large-v3-turbo"
}
```
