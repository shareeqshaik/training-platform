import { useEffect, useRef } from "react";
const CLIENT_ID = "524566616253-gbujjrau57crtic9fcs8c4i67va6n8g7.apps.googleusercontent.com";
export default function GoogleButton({ onCredential }) {
  const box = useRef(null);
  useEffect(() => {
    const init = () => {
      window.google.accounts.id.initialize({ client_id: CLIENT_ID, callback: r => onCredential(r.credential) });
      window.google.accounts.id.renderButton(box.current, { theme: "filled_blue", size: "large", text: "signin_with", width: 300 });
    };
    if (window.google?.accounts?.id) { init(); return; }
    const s = document.createElement("script");
    s.src = "https://accounts.google.com/gsi/client"; s.async = true; s.onload = init;
    document.body.appendChild(s);
  }, []);
  return <div ref={box} style={{ display: "flex", justifyContent: "center", marginTop: 14 }} />;
}