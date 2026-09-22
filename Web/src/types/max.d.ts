export {};

declare global {
  interface Window {
    WebApp?: {
      initData: string;

      initDataUnsafe?: {
        query_id?: string;
        auth_date?: number;
        hash?: string;

        user?: {
          id: number;
          first_name?: string;
          last_name?: string;
          username?: string;
          language_code?: string;
          photo_url?: string;
        };

        chat?: {
          id: number;
          type: "DIALOG" | "CHAT" | "CHANNEL";
        };

        start_param?: string;
      };

      platform?: string;
      version?: string;
      deviceName?: string;

      openLink?: (url: string) => void;
      openMaxLink?: (url: string) => void;
    };
  }
}