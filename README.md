# 🚀 Advanced SMTP Office365/Outlook Checker

Un script Python avancé pour vérifier des identifiants SMTP Office365/Outlook avec des fonctionnalités modernes et robustes.

## ✨ Fonctionnalités

- **🔐 Vérification SMTP avancée** : Connexion sécurisée à `smtp.office365.com` avec STARTTLS
- **⚡ Multi-threading** : Traitement parallèle avec ThreadPoolExecutor (5-10 threads configurables)
- **📧 Test d'envoi d'email** : Envoi automatique d'emails de test vers une adresse de contrôle
- **📱 Notifications Telegram** : Alertes instantanées quand des identifiants valides sont trouvés
- **🎨 Interface colorée** : Sortie console avec codes couleur pour une meilleure lisibilité
- **📊 Rapports détaillés** : Statistiques complètes et résumé final
- **🔧 Format flexible** : Support des séparateurs `:`, `;` et `|`
- **⏱️ Gestion intelligente des délais** : Délais aléatoires pour éviter les blocages
- **🛡️ Gestion d'erreurs robuste** : Classification détaillée des erreurs (timeout, SSL, auth, etc.)
- **📁 Logs complets** : Sauvegarde des résultats dans des fichiers séparés

## 📦 Installation

1. Clonez le repository :
```bash
git clone https://github.com/wKayaa/smtpcheck.git
cd smtpcheck
```

2. Installez les dépendances :
```bash
pip install -r requirements.txt
```

3. Configurez le script (optionnel) :
```bash
cp config.json.example config.json
# Éditez config.json avec vos paramètres
```

## 🚀 Utilisation

1. **Préparez votre fichier de combos** (`combos.txt`) :
```
user1@outlook.com:password123
user2@hotmail.com:mypassword
test@office365.com;anotherpass
admin@live.com|secretpassword
```

2. **Lancez le script** :
```bash
python3 smtpcheck.py
```

3. **Résultats** :
   - `valid.txt` : Identifiants valides
   - `invalid.txt` : Identifiants invalides
   - `errors.txt` : Erreurs techniques
   - `smtp_checker.log` : Logs détaillés

## ⚙️ Configuration

### Fichier de configuration (`config.json`)

```json
{
    "smtp_server": "smtp.office365.com",
    "smtp_port": 587,
    "smtp_timeout": 10,
    "max_threads": 8,
    "delay_range": [1, 5],
    "test_email_recipient": "your-test-email@gmail.com",
    "telegram_bot_token": "YOUR_BOT_TOKEN_HERE",
    "telegram_chat_id": "YOUR_CHAT_ID_HERE",
    "input_file": "combos.txt",
    "valid_file": "valid.txt",
    "invalid_file": "invalid.txt",
    "log_file": "smtp_checker.log"
}
```

### Paramètres disponibles

- `smtp_server` : Serveur SMTP (par défaut: smtp.office365.com)
- `smtp_port` : Port SMTP (par défaut: 587)
- `smtp_timeout` : Timeout en secondes (par défaut: 10)
- `max_threads` : Nombre de threads simultanés (par défaut: 8)
- `delay_range` : Délai aléatoire entre tests [min, max] secondes
- `test_email_recipient` : Email de test pour vérifier la livraison
- `telegram_bot_token` : Token du bot Telegram pour notifications
- `telegram_chat_id` : ID du chat Telegram pour notifications

## 📱 Configuration Telegram

1. **Créez un bot Telegram** :
   - Parlez à [@BotFather](https://t.me/botfather)
   - Utilisez `/newbot` et suivez les instructions
   - Notez le token du bot

2. **Obtenez votre Chat ID** :
   - Parlez à [@userinfobot](https://t.me/userinfobot)
   - Ou utilisez l'API : `https://api.telegram.org/bot<TOKEN>/getUpdates`

3. **Configurez dans `config.json`** :
```json
{
    "telegram_bot_token": "123456789:ABCdefGHIjklmnop-QRStuVWXyza1234567",
    "telegram_chat_id": "123456789"
}
```

## 🎨 Format de sortie

### Console
```
🚀 Starting Advanced SMTP Checker
[VALID] user@outlook.com:password123
[INVALID] test@hotmail.com - Auth failed
[SSL_ERROR] problem@live.com - SSL error
Progress: 10/100 (10.0%)

==================== 📊 FINAL SUMMARY ====================
📈 Total Combos Tested: 100
✅ Valid Credentials: 15
❌ Invalid Credentials: 80
⚠️  Errors: 5
⏱️  Total Time: 45.30 seconds
📊 Success Rate: 15.00%
```

### Notification Telegram
```
🔑 Valid SMTP Credentials Found

📧 Email: user@outlook.com
🔐 Password: password123
✅ Status: valid
📨 Test Email: Sent
📬 Deliverability: sent

⏰ Time: 2024-01-01 12:00:00
```

## 🔧 Fonctionnalités avancées

### Multi-format Support
Le script supporte plusieurs formats de séparateurs :
- `email:password`
- `email;password`
- `email|password`

### Gestion d'erreurs intelligente
- `[VALID]` : Identifiants corrects
- `[INVALID]` : Authentification échouée
- `[SSL_ERROR]` : Problème de certificat SSL
- `[SMTP_ERROR]` : Erreur du serveur SMTP
- `[DISCONNECTED]` : Déconnexion du serveur
- `[TIMEOUT]` : Dépassement du délai
- `[ERROR]` : Erreur inattendue

### Anti-ban Features
- Délais aléatoires entre les connexions
- Limitation du nombre de threads simultanés
- Gestion des timeouts configurables
- Classification des erreurs pour éviter les retests inutiles

## 📊 Statistiques et Monitoring

Le script fournit des statistiques détaillées :
- Nombre total de combos testés
- Taux de succès en pourcentage
- Temps d'exécution total
- Distribution des erreurs
- Historique complet dans les logs

## ⚠️ Avertissements

- **Utilisation légale uniquement** : Ne testez que des comptes dont vous êtes propriétaire
- **Respect des ToS** : Respectez les conditions d'utilisation des services
- **Rate limiting** : Utilisez des délais appropriés pour éviter les blocages
- **Sécurité** : Ne partagez jamais vos tokens Telegram ou identifiants

## 🤝 Contribution

Les contributions sont bienvenues ! N'hésitez pas à :
- Ouvrir des issues pour signaler des bugs
- Proposer des améliorations
- Soumettre des pull requests

## 📜 Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.

## 🔗 Support

Pour du support ou des questions :
- Ouvrez une issue sur GitHub
- Contactez via Telegram (si configuré)

---

**⚡ Happy SMTP Checking! ⚡**