# Release documentation

## Release process

### 1 Clean environment

    ```bash
    make clean    # delete all temp files
    make prepare  # commit deletions
    ```
### 2 Python package

1. Bump version of databrickslabs_jupyterlab

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

2. Create distribution

    ```bash
    make dist
    ```

3. Create and tag release

    ```bash
    make release
    ```

4. Deploy to pypi

    ```bash
    make upload
    ```

### 3 Labextension

1. Change into folder `ssh_ipykernel_interrupt` and the follow 2
### 4 Push repo and tag

    ```bash
    git push
    git push origin --tags
    ```
