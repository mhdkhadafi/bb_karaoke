#!/bin/bash

# Define the Zotify config path
CONFIG_FILE="/home/$USER/.config/zotify/config.json"

# Update the "CREDENTIALS_LOCATION" key with the value of the environment variable
if [ -f "$CONFIG_FILE" ]; then
    # Use jq to modify the config file if the credentials location environment variable is set
    jq --arg loc "$ZOTIFY_CREDENTIALS_LOCATION" '.CREDENTIALS_LOCATION = $loc' "$CONFIG_FILE" > /tmp/config.json && mv /tmp/config.json "$CONFIG_FILE"
    echo "Zotify config updated: CREDENTIALS_LOCATION set to $ZOTIFY_CREDENTIALS_LOCATION"
else
    echo "Zotify config file not found!"
fi