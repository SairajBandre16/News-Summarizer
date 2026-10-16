"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";

const noopSubscribe = () => () => {};

/** False during SSR and hydration, true afterwards. */
export function useMounted() {
  return useSyncExternalStore(noopSubscribe, () => true, () => false);
}

// ---------------------------------------------------------------------------
// Saved stories, kept in localStorage and synced across tabs.
// ---------------------------------------------------------------------------

const SAVED_KEY = "blitzfeed:saved";
const SAVED_EVENT = "blitzfeed:saved-change";
const SAVED_LIMIT = 200;
const EMPTY = [];
let savedSnapshot = { raw: null, value: EMPTY };

function readSaved() {
  let raw = null;
  try {
    raw = localStorage.getItem(SAVED_KEY);
  } catch {
    return EMPTY;
  }
  if (raw === savedSnapshot.raw) return savedSnapshot.value;
  let value = EMPTY;
  try {
    const parsed = JSON.parse(raw ?? "[]");
    if (Array.isArray(parsed)) value = parsed;
  } catch {}
  savedSnapshot = { raw, value };
  return value;
}

function writeSaved(list) {
  try {
    localStorage.setItem(SAVED_KEY, JSON.stringify(list));
  } catch {}
  window.dispatchEvent(new Event(SAVED_EVENT));
}

function subscribeSaved(callback) {
  window.addEventListener("storage", callback);
  window.addEventListener(SAVED_EVENT, callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(SAVED_EVENT, callback);
  };
}

export function useSaved() {
  const saved = useSyncExternalStore(subscribeSaved, readSaved, () => EMPTY);

  const isSaved = useCallback((id) => saved.some((a) => a.id === id), [saved]);

  const toggle = useCallback((article) => {
    const list = readSaved();
    if (list.some((a) => a.id === article.id)) {
      writeSaved(list.filter((a) => a.id !== article.id));
      return;
    }
    const { id, title, description, url, image, source, publishedAt, summarizable, sig } = article;
    const entry = { id, title, description, url, image, source, publishedAt, summarizable, sig };
    writeSaved([{ ...entry, savedAt: new Date().toISOString() }, ...list].slice(0, SAVED_LIMIT));
  }, []);

  const clear = useCallback(() => writeSaved([]), []);

  return { saved, isSaved, toggle, clear };
}

// ---------------------------------------------------------------------------
// Text to speech with the browser's built-in voices.
// ---------------------------------------------------------------------------

function pickVoice(voices) {
  const english = voices.filter((v) => v.lang?.toLowerCase().startsWith("en"));
  return (
    english.find((v) => /natural|neural|online/i.test(v.name)) ??
    english.find((v) => /google|samantha|daniel|aria|jenny/i.test(v.name)) ??
    english[0] ??
    null
  );
}

/** Chrome stops long utterances after ~15s, so speak sentence-sized chunks. */
function chunk(text) {
  const sentences = text.match(/[^.!?]+[.!?]+["')\]]*|\S[^.!?]*$/g) ?? [text];
  const chunks = [];
  let current = "";
  for (const sentence of sentences) {
    if ((current + sentence).length > 220 && current) {
      chunks.push(current.trim());
      current = "";
    }
    current += `${sentence} `;
  }
  if (current.trim()) chunks.push(current.trim());
  return chunks;
}

export function useSpeech() {
  const supported = useSyncExternalStore(
    noopSubscribe,
    () => "speechSynthesis" in window,
    () => false,
  );
  const [speaking, setSpeaking] = useState(false);
  const utterances = useRef([]);

  const stop = useCallback(() => {
    window.speechSynthesis?.cancel();
    utterances.current = [];
    setSpeaking(false);
  }, []);

  const speak = useCallback((text) => {
    const synth = window.speechSynthesis;
    if (!synth) return;
    synth.cancel();
    const voice = pickVoice(synth.getVoices());
    const parts = chunk(text);
    // Hold references so Chrome doesn't garbage-collect utterances mid-speech.
    utterances.current = parts.map((part, index) => {
      const utterance = new SpeechSynthesisUtterance(part);
      utterance.rate = 1.03;
      if (voice) utterance.voice = voice;
      const finish = () => {
        utterances.current = [];
        setSpeaking(false);
      };
      utterance.onerror = finish;
      if (index === parts.length - 1) utterance.onend = finish;
      return utterance;
    });
    utterances.current.forEach((u) => synth.speak(u));
    setSpeaking(true);
  }, []);

  // Stop on unmount, but only if this component is the one speaking.
  useEffect(
    () => () => {
      if (utterances.current.length) window.speechSynthesis?.cancel();
    },
    [],
  );

  return { supported, speaking, speak, stop };
}
