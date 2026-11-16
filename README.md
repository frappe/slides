> [!IMPORTANT]
> Slides has moved to [Frappe Suite](https://github.com/frappe/suite). This repository is now archived.

<div align="center">

<a href="https://frappe.io/products/">
    <img src="https://github.com/user-attachments/assets/21642db8-1170-4a0d-b973-53bbedcd6259" height="80" alt="Frappe slides Logo">
</a>

<h1>Frappe Slides</h1>

<div>
    <picture>
        <!-- <source media="(prefers-color-scheme: dark)" srcset="https://github.com/user-attachments/assets/7b013cc1-fe40-4b3c-a765-d8c3697bf81e"> -->
        <img width="1402" alt="Frappe Slide Screenshot" src="https://github.com/user-attachments/assets/3bb8ba8c-a5a1-4223-bf04-cd07372128a0">
    </picture>
</div>
</div>

## Local Setup

1. [Setup Bench](https://docs.frappe.io/framework/user/en/installation).
1. In the frappe-bench directory, run `bench start` and keep it running.
1. Open a new terminal session and cd into `frappe-bench` directory and run following commands:

```bash
bench get-app slides
bench new-site slides.localhost --install-app slides
bench browse slides.localhost --user Administrator
bench --site slides.localhost set-config ignore_csrf 1 # prevents CSRFToken errors while using the vite dev server
```

1. Access the slides page at `slides.localhost:8000/slides` in your web browser.

**For Frontend Development**

1. Open a new terminal session and run the following commands:

```bash
cd frappe-bench/apps/slides
yarn install
yarn dev --host
```

1. Now, you can access the site on vite dev server at `http://slides.localhost:8080`

**Note:** You'll find all the code related to slides's frontend inside `frappe-bench/apps/slides/frontend`

<h2></h2>

<br>
<br>
<div align="center">
	<a href="https://frappe.io" target="_blank">
		<picture>
			<source media="(prefers-color-scheme: dark)" srcset="https://frappe.io/files/Frappe-white.png">
			<img src="https://frappe.io/files/Frappe-black.png" alt="Frappe Technologies" height="28"/>
		</picture>
	</a>
</div>
