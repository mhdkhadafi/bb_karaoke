#!/bin/bash

# Define the path to the credentials template
TEMPLATE_FILE="/app/zotify_credentials.json"
FINAL_FILE="/app/zotify_credentials_final.json"

# Replace placeholders with environment variables
sed "s/<USERNAME>/$ZOTIFY_USERNAME/g" $TEMPLATE_FILE | \
sed "s/<AUTHDATA>/$ZOTIFY_AUTHDATA/g" > $FINAL_FILE

echo "Zotify credentials have been updated."
