# Образ для чекеров каталогов (Glama и подобных): собрать и запустить сервер.
# Без DAEPAK_API_KEY сервер стартует, отвечает на initialize, tools/list отдаёт
# пустой каталог — этого достаточно для интроспекции; ключ добавляет инструменты.
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md daepak_agent_mcp.py ./
RUN pip install --no-cache-dir .
ENTRYPOINT ["daepak-mcp"]
