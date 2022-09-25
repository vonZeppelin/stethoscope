;; kudos to https://github.com/bliksemman/boot-gh-pages
(ns deploy
  (:require
   [clojure.java.io :refer [file input-stream]]
   [clojure.java.shell :refer [sh with-sh-dir]])
  (:import
   java.io.SequenceInputStream
   java.nio.file.FileSystems
   java.util.Collections))

(def deploy-branch "refs/heads/gh-pages")
(def deploy-dir (file "public/"))
(def deploy-ignore ["js/cljs-runtime/**" "js/*.edn"])

(def git-import-header
  (str
   "commit " deploy-branch "\n"
   "committer deploy.clj <deploy@lbogdanov.dev> now\n"
   "data 0\n\n"))

(defn- abort []
  (System/exit 1))

(defn- git-import-data []
  (let [fs (FileSystems/getDefault)
        ignore-matchers (map
                         #(.getPathMatcher fs (str "glob:" %))
                         deploy-ignore)
        deploy-dir-relative-path (fn [f]
                                   (-> deploy-dir
                                       .toPath
                                       (.relativize (.toPath f))))
        ignore-file? (fn [f]
                       (or
                        (.isDirectory f)
                        (let [path (deploy-dir-relative-path f)]
                          (some #(.matches % path) ignore-matchers))))
        str->input-stream (fn [s]
                            (input-stream (.getBytes s "UTF-8")))
        git-modified-line (fn [f]
                            (format
                             "M 644 inline %s\ndata %d\n"
                             (deploy-dir-relative-path f)
                             (.length f)))]
    (SequenceInputStream.
     (str->input-stream git-import-header)
     (->> deploy-dir
          file-seq
          (remove ignore-file?)
          (map (fn [f]
                 (println "* " (str f))
                 f))
          (reduce
           (fn [acc f]
             (-> [acc
                  (str->input-stream (git-modified-line f))
                  (input-stream f)
                  (str->input-stream "\n")]
                 Collections/enumeration
                 SequenceInputStream.))
           (str->input-stream ""))))))

(defn- git [& args]
  (let [{:keys [exit err]} (apply sh "git" args)]
    (when-not (zero? exit)
      (println err)
      (abort))))

(defn- git-fast-import []
  (println "Adding files to deploy...")
  (git "fast-import" "--date-format=now" "--force" :in (git-import-data)))

(defn- git-push []
  (println "Pushing to the repository...")
  (git "push" "--force" "origin" deploy-branch))

(defn -main []
  (when-not (.isDirectory deploy-dir)
    (println "Deploy directory does not exist – aborting!")
    (abort))
  (when (empty? (.list deploy-dir))
    (println "Deploy directory is empty – aborting!")
    (abort))
  (with-sh-dir "."
    (git-fast-import)
    (git-push)))
