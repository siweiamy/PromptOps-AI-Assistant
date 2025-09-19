# Use official Python image
FROM 187669607111.dkr.ecr.us-east-1.amazonaws.com/devops/python:3.13-slim

# Set working directory
WORKDIR /app

# Create non-root user with home directory for security
RUN groupadd appuser && useradd -m -g appuser appuser

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy templates folder first
COPY --chown=appuser:appuser templates/ ./templates/

# Copy application code with proper ownership
COPY --chown=appuser:appuser app.py .
COPY --chown=appuser:appuser adapter_with_error_handler.py .
COPY --chown=appuser:appuser incident_bot.py .
COPY --chown=appuser:appuser common_function.py .

# Copy application code with proper ownership
COPY --chown=appuser:appuser start.sh .

# Update permissions
RUN chmod +x /app/start.sh

# Set default port (can be overridden at runtime)
ENV PORT=5000

# Switch to non-root user
USER appuser

# Expose port (default 5000, but configurable via ENV)
EXPOSE $PORT

# Add health check using Python instead of curl (using dynamic port)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request, os; urllib.request.urlopen(f'http://localhost:{os.getenv(\"PORT\", \"5000\")}/', timeout=5)" || exit 1

# Use exec form for better signal handling
ENTRYPOINT ["/app/start.sh"]
