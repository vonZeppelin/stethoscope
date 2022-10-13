(ns stethoscope.effects
  (:require [re-frame.core :as rf]))

(rf/reg-fx
 :timeout
 (fn [{:keys [event timeout]
       :or {timeout 0.15}}]
   (js/setTimeout
    #(rf/dispatch [event])
    (* timeout 1000))))
