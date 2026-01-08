# Skript pro spuštění testů
echo "🧪 Spouštím testy..."
echo ""

# Aktivuj venv pokud existuje
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Spusť pytest
pytest tests/ -v --cov=src --cov-report=term --cov-report=html

echo ""
echo "✅ Testy dokončeny!"
echo "📊 Coverage report: htmlcov/index.html"
