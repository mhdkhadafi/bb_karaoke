#!/bin/bash

mkdir -p /app/zotify

# Define the path to the credentials template
TEMPLATE_FILE="/app/zotify_credentials.json"
CREDENTIALS_FILE="/app/zotify/credentials.json"

# Replace placeholders with environment variables
sed "s/<USERNAME>/$ZOTIFY_USERNAME/g" $TEMPLATE_FILE | \
sed "s/<AUTHDATA>/$ZOTIFY_AUTHDATA/g" > $CREDENTIALS_FILE

echo "Zotify credentials have been updated."

CONFIG_TEMPLATE_FILE="/app/zotify_config.json"
CONFIG_FINAL_FILE="/root/.config/zotify/config.json"

# Ensure the directory exists
mkdir -p /root/.config/zotify

# Replace the <CREDENTIALS_LOCATION> placeholder with the correct path in the template
sed "s|<CREDENTIALS_LOCATION>|$CREDENTIALS_FILE|g" $CONFIG_TEMPLATE_FILE > $CONFIG_FINAL_FILE

echo "Zotify config file has been created at $CONFIG_FINAL_FILE"
