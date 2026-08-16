/**
 * Google Places API (New) — Text Search.
 *
 * Requires GOOGLE_PLACES_API_KEY. Get one at console.cloud.google.com, enable
 * "Places API (New)", and restrict the key. The free monthly credit covers early
 * list-building comfortably; set a billing cap anyway.
 *
 * Only the fields listed in FIELD_MASK are requested — Places bills by field mask,
 * so asking for less genuinely costs less.
 */
const ENDPOINT = 'https://places.googleapis.com/v1/places:searchText';

const FIELD_MASK = [
  'places.id',
  'places.displayName',
  'places.formattedAddress',
  'places.nationalPhoneNumber',
  'places.websiteUri',
  'places.rating',
  'places.userRatingCount',
  'nextPageToken',
].join(',');

/**
 * @returns {Promise<Array>} normalised business records
 */
export async function searchPlaces({ query, apiKey, maxPages = 3 }) {
  if (!apiKey) throw new Error('GOOGLE_PLACES_API_KEY is not set');

  const results = [];
  let pageToken;

  for (let page = 0; page < maxPages; page++) {
    const body = { textQuery: query, maxResultCount: 20 };
    if (pageToken) body.pageToken = pageToken;

    const res = await fetch(ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': apiKey,
        'X-Goog-FieldMask': FIELD_MASK,
      },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Places API ${res.status}: ${text.slice(0, 300)}`);
    }

    const data = await res.json();
    for (const p of data.places ?? []) {
      results.push({
        placeId:     p.id,
        business:    p.displayName?.text ?? '',
        address:     p.formattedAddress ?? null,
        phone:       p.nationalPhoneNumber ?? null,
        website:     p.websiteUri ?? null,
        rating:      p.rating ?? null,
        reviewCount: p.userRatingCount ?? 0,
      });
    }

    pageToken = data.nextPageToken;
    if (!pageToken) break;
    // Places requires a short pause before a page token becomes valid.
    await new Promise(r => setTimeout(r, 2000));
  }

  return results;
}
