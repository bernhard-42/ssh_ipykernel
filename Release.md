# Release documentation

## 1 Release process

1. Clean environment

    ```bash
    make clean    # delete all temp files
    make prepare  # commit deletions
    ```

2. Bump version of databrickslabs_jupyterlab

    - A new release candidate with rc0

      ```bash
      make bump part=major|minor|patch
      ```

    - A new build

      ```bash
      make bump part=build
      ```

    - A new release

      ```bash
      make bump part=release
      ```

    - A new release without release candidate

      ```bash
      make bump part=major|minor|patch version=major.minor.patch
      ```

3. Create distribution

    ```bash
    make dist
    ```

4. Create and tag release

    ```bash
    make release
    ```

5. Deploy to pypi

    ```bash
    make upload
    ```

6. Push repo and tag

    ```bash
    git push
    git push origin --tags
    ```
