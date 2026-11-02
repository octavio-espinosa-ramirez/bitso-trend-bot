# Desplegar v4 en Railway

1. Sube SOLO la carpeta v4 a un repo nuevo de GitHub (privado). El .gitignore ya excluye .env y state.json.
2. Railway > New Project > Deploy from GitHub repo > elige ese repo.
3. Variables (pestaña Variables). En PAPER solo hace falta:
       TOKEN=<token de tu bot de Telegram>
   (NO pongas BITSO_API_KEY/SECRET hasta que decidas operar en real.)
4. Volumen: pestaña Settings > Volumes > Add Volume, ruta de montaje: /data
   (ahí se guarda state.json; sin volumen el estado se pierde en cada deploy).
5. Antes de desplegar: detén el bot local (Ctrl+C) y el servicio viejo de Railway, si existe.
   Dos instancias con el mismo TOKEN se pelean los mensajes de Telegram.
6. Deploy. En Logs debe verse el inicio y en Telegram "Bot v4 iniciado. Modo PAPER".
