#!/bin/bash
# Test deployment configuration

echo "🧪 Testing Remembar Deployment Configuration"
echo "=" echo ""

# Check for required files
echo "1. Checking deployment files..."
files=("railway.toml" "railway.json" "nixpacks.toml" ".railwayignore" "api-service/Procfile" "api-service/requirements.txt")

all_present=true
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✓ $file"
    else
        echo "   ❌ Missing: $file"
        all_present=false
    fi
done

# Check Procfile content
echo ""
echo "2. Checking Procfile..."
if grep -q "uvicorn main:app" api-service/Procfile; then
    echo "   ✓ Procfile has correct command"
else
    echo "   ❌ Procfile missing uvicorn command"
    all_present=false
fi

# Check main.py for PORT handling
echo ""
echo "3. Checking main.py PORT handling..."
if grep -q "PORT" api-service/main.py; then
    echo "   ✓ main.py handles PORT environment variable"
else
    echo "   ❌ main.py doesn't handle PORT variable"
    all_present=false
fi

# Check requirements.txt
echo ""
echo "4. Checking requirements.txt..."
required_packages=("fastapi" "uvicorn" "httpx" "reka-api" "mcp")
for package in "${packages[@]}"; do
    if grep -q "$package" api-service/requirements.txt; then
        echo "   ✓ $package"
    else
        echo "   ⚠️  $package might be missing"
    fi
done

# Summary
echo ""
echo "=" * 50
if [ "$all_present" = true ]; then
    echo "✅ All deployment configuration files are present!"
    echo ""
    echo "Ready to deploy!"
    echo ""
    echo "Next steps:"
    echo "  1. railway login --browserless"
    echo "  2. railway init"
    echo "  3. railway variables set REKA_API_KEY=your_key"
    echo "  4. railway up"
    echo ""
    echo "See DEPLOY_QUICK_START.md for details"
else
    echo "❌ Some files are missing. Check above for details."
    exit 1
fi

