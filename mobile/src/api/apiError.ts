/**
 * apiError.ts
 * Shared error class for API responses.
 * Separated to avoid circular imports between client.ts and secureClient.ts.
 */
export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}
