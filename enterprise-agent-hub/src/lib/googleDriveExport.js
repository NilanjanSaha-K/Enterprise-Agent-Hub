import { gapi } from "gapi-script";

const DISCOVERY_DOCS = [
  "https://www.googleapis.com/discovery/v1/apis/drive/v3/rest",
  "https://docs.googleapis.com/$discovery/rest?version=v1",
  "https://sheets.googleapis.com/$discovery/rest?version=v4"
];

let tokenClient;
let gapiInited = false;
let gisInited = false;
let config = { apiKey: null, clientId: null };

/**
 * Initialize BOTH the GAPI client (for making requests) 
 * AND the GIS client (for logging in).
 */
export const initGoogleClient = async () => {
  try {
    // 1. Fetch Config
    if (!config.apiKey || !config.clientId) {
        console.log("Fetching Google config from backend...");
        const response = await fetch("/api/config");
        config = await response.json();
    }

    // 2. Load GAPI (The Request Library)
    await new Promise((resolve) => {
      gapi.load("client", async () => {
        await gapi.client.init({
          apiKey: config.apiKey,
          discoveryDocs: DISCOVERY_DOCS,
        });
        gapiInited = true;
        console.log("✅ GAPI Client Loaded");
        resolve();
      });
    });

    // 3. Load GIS (The New Auth Library)
    await new Promise((resolve) => {
      const script = document.createElement("script");
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      script.onload = () => {
        tokenClient = google.accounts.oauth2.initTokenClient({
          client_id: config.clientId,
          scope: "https://www.googleapis.com/auth/drive.file",
          callback: '', // defined at request time
        });
        gisInited = true;
        console.log("✅ GIS Auth Loaded");
        resolve();
      };
      document.body.appendChild(script);
    });

  } catch (err) {
    console.error("Init Error:", err);
  }
};

/**
 * Helper to get a valid Access Token
 */
const getToken = async () => {
  if (!gapiInited || !gisInited) await initGoogleClient();

  return new Promise((resolve, reject) => {
    // Check if we already have a valid token in gapi
    if (gapi.client.getToken() !== null) {
      resolve(true);
      return;
    }

    // If not, trigger the popup
    tokenClient.callback = (resp) => {
      if (resp.error) {
        reject(resp);
      }
      resolve(resp);
    };
    
    // Prompt the user
    tokenClient.requestAccessToken({ prompt: 'consent' });
  });
};

// --- EXPORT TO DOCS ---
export const createUserDoc = async (title, content) => {
  await getToken(); // Ensure we are logged in

  // Create Blank Doc
  const createResponse = await gapi.client.docs.documents.create({
    resource: { title: title }
  });
  const docId = createResponse.result.documentId;

  // Insert Text
  await gapi.client.docs.documents.batchUpdate({
    documentId: docId,
    resource: {
      requests: [{ insertText: { location: { index: 1 }, text: content } }]
    }
  });

  return `https://docs.google.com/document/d/${docId}/edit`;
};

// --- EXPORT TO SHEETS ---
export const createUserSheet = async (title, csvData) => {
  await getToken(); // Ensure we are logged in

  const createResponse = await gapi.client.sheets.spreadsheets.create({
    resource: { properties: { title: title } }
  });
  const spreadsheetId = createResponse.result.spreadsheetId;

  await gapi.client.sheets.spreadsheets.values.update({
    spreadsheetId: spreadsheetId,
    range: "Sheet1!A1",
    valueInputOption: "RAW",
    resource: {
      values: csvData.split('\n').map(r => r.split(','))
    }
  });

  return `https://docs.google.com/spreadsheets/d/${spreadsheetId}/edit`;
};