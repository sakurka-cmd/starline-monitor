// Backend API proxy helper
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function proxyToBackend(
  endpoint: string,
  options: {
    method?: string;
    body?: unknown;
    headers?: HeadersInit;
  } = {}
): Promise<Response> {
  const { method = 'GET', body, headers = {} } = options;

  const fetchOptions: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  };

  if (body) {
    fetchOptions.body = JSON.stringify(body);
  }

  const response = await fetch(`${BACKEND_URL}/api${endpoint}`, fetchOptions);
  return response;
}

export { BACKEND_URL };
